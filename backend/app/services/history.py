"""Chat history service.

CRUD layer for stored_chats and stored_messages.
All functions use the db_cursor() context manager from connect.py so
connections are properly managed (commit / rollback / close).

Sender encoding (stored_messages.sender is an INT column per schema):
    SENDER_USER  = 0  — message typed by the human user
    SENDER_AGENT = 1  — message produced by the AI agent
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache

from loguru import logger

from backend.database.connect import db_cursor

# ---------------------------------------------------------------------------
# Sender constants  (match the INT CHECK constraint in the schema)
# ---------------------------------------------------------------------------
SENDER_USER: int = 0
SENDER_AGENT: int = 1


@lru_cache(maxsize=1)
def ensure_history_schema() -> None:
    """Repair older history tables so the current API can persist chats safely."""
    with db_cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS stored_chats (
                id SERIAL PRIMARY KEY,
                user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                agent_type TEXT CHECK (agent_type IN ('housing', 'market')),
                title TEXT
            )
            """
        )
        cur.execute("ALTER TABLE stored_chats ADD COLUMN IF NOT EXISTS agent_type TEXT")
        cur.execute("ALTER TABLE stored_chats ADD COLUMN IF NOT EXISTS title TEXT")
        cur.execute(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'stored_chats' AND column_name = 'users_id'
                ) THEN
                    ALTER TABLE stored_chats ALTER COLUMN users_id DROP NOT NULL;
                END IF;
            END
            $$;
            """
        )
        cur.execute("CREATE SEQUENCE IF NOT EXISTS stored_chats_id_seq")
        cur.execute(
            """
            SELECT setval(
                'stored_chats_id_seq',
                COALESCE((SELECT MAX(id) FROM stored_chats), 0) + 1,
                false
            )
            """
        )
        cur.execute(
            "ALTER TABLE stored_chats ALTER COLUMN id SET DEFAULT nextval('stored_chats_id_seq')"
        )
        cur.execute(
            "ALTER TABLE stored_chats ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP"
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS stored_messages (
                id SERIAL PRIMARY KEY,
                chat_id INT NOT NULL REFERENCES stored_chats(id) ON DELETE CASCADE,
                sender INT NOT NULL CHECK (sender IN (0, 1)),
                message TEXT NOT NULL,
                metadata JSONB NOT NULL DEFAULT '{}',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cur.execute(
            """
            ALTER TABLE stored_messages
            ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'
            """
        )
        cur.execute(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'stored_messages' AND column_name = 'embedding'
                ) THEN
                    ALTER TABLE stored_messages ALTER COLUMN embedding DROP NOT NULL;
                END IF;
            END
            $$;
            """
        )
        cur.execute("CREATE SEQUENCE IF NOT EXISTS stored_messages_id_seq")
        cur.execute(
            """
            SELECT setval(
                'stored_messages_id_seq',
                COALESCE((SELECT MAX(id) FROM stored_messages), 0) + 1,
                false
            )
            """
        )
        cur.execute(
            """
            ALTER TABLE stored_messages
            ALTER COLUMN id SET DEFAULT nextval('stored_messages_id_seq')
            """
        )
        cur.execute(
            "ALTER TABLE stored_messages ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP"
        )
    logger.debug("history | ensured schema compatibility")


# ---------------------------------------------------------------------------
# Data-transfer objects
# ---------------------------------------------------------------------------


@dataclass
class ChatSummary:
    id: int
    user_id: int
    agent_type: str | None  # 'housing' | 'market' | None (UI extension col)
    title: str | None
    created_at: datetime


@dataclass
class MessageRecord:
    id: int
    chat_id: int
    sender: int  # 0 = SENDER_USER, 1 = SENDER_AGENT (raw DB value)
    sender_label: str  # 'user' | 'agent'  (derived — use in API responses)
    message: str
    metadata: dict  # sql_used, rows_found, error, etc.
    created_at: datetime


# ---------------------------------------------------------------------------
# Chat (session) operations
# ---------------------------------------------------------------------------


def create_chat(user_id: int, agent_type: str | None = None, title: str | None = None) -> int:
    """Create a new chat session and return its auto-generated ID.

    Args:
        user_id:    ID of the authenticated user.
        agent_type: 'housing' or 'market'.
        title:      Optional display label (can be set/updated later).

    Returns:
        The new chat's integer ID.
    """
    ensure_history_schema()
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO stored_chats (user_id, agent_type, title)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (user_id, agent_type, title),
        )
        row = cur.fetchone()
        chat_id: int = row[0]
    logger.debug("history | created chat id={} user={}", chat_id, user_id)
    return chat_id


def get_user_chats(user_id: int, limit: int = 20) -> list[ChatSummary]:
    """Return a user's chat sessions, most recent first.

    Args:
        user_id: The authenticated user's ID.
        limit:   Max number of sessions to return (default 20).

    Returns:
        List of ChatSummary ordered by created_at DESC.
    """
    ensure_history_schema()
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT id, user_id, agent_type, title, created_at
            FROM stored_chats
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (user_id, limit),
        )
        rows = cur.fetchall()

    return [
        ChatSummary(
            id=r[0],
            user_id=r[1],
            agent_type=r[2],
            title=r[3],
            created_at=r[4],
        )
        for r in rows
    ]


def get_chat_by_id(chat_id: int, user_id: int) -> ChatSummary | None:
    """Return a single chat session if it belongs to the given user.

    Returns None if not found or the chat belongs to a different user.
    """
    ensure_history_schema()
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT id, user_id, agent_type, title, created_at
            FROM stored_chats
            WHERE id = %s AND user_id = %s
            """,
            (chat_id, user_id),
        )
        row = cur.fetchone()

    if row is None:
        return None
    return ChatSummary(
        id=row[0],
        user_id=row[1],
        agent_type=row[2],
        title=row[3],
        created_at=row[4],
    )


def update_chat_title(chat_id: int, user_id: int, title: str) -> bool:
    """Update the display title for a chat.  Returns True if updated."""
    ensure_history_schema()
    with db_cursor() as cur:
        cur.execute(
            """
            UPDATE stored_chats SET title = %s
            WHERE id = %s AND user_id = %s
            """,
            (title, chat_id, user_id),
        )
        updated = cur.rowcount > 0
    return updated


# ---------------------------------------------------------------------------
# Message operations
# ---------------------------------------------------------------------------


def save_message(
    chat_id: int,
    sender: int,
    message: str,
    metadata: dict | None = None,
) -> int:
    """Append a message to a chat and return its ID.

    Args:
        chat_id:  The parent chat session ID.
        sender:   SENDER_USER (0) or SENDER_AGENT (1).
        message:  The message text.
        metadata: Optional dict stored as JSONB (sql_used, rows_found, error …).

    Returns:
        The new message's integer ID.
    """
    ensure_history_schema()
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO stored_messages (chat_id, sender, message, metadata)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (chat_id, sender, message, json.dumps(metadata or {})),
        )
        row = cur.fetchone()
        msg_id: int = row[0]
    logger.debug("history | saved message id={} chat={} sender={}", msg_id, chat_id, sender)
    return msg_id


def get_chat_messages(chat_id: int, limit: int = 100) -> list[MessageRecord]:
    """Return all messages for a chat in chronological (oldest-first) order.

    Args:
        chat_id: The chat session ID.
        limit:   Max number of messages to return (default 100).

    Returns:
        List of MessageRecord ordered by created_at ASC.
    """
    ensure_history_schema()
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT id, chat_id, sender, message, metadata, created_at
            FROM stored_messages
            WHERE chat_id = %s
            ORDER BY created_at ASC
            LIMIT %s
            """,
            (chat_id, limit),
        )
        rows = cur.fetchall()

    return [
        MessageRecord(
            id=r[0],
            chat_id=r[1],
            sender=r[2],
            sender_label="user" if r[2] == SENDER_USER else "agent",
            message=r[3],
            # psycopg2 returns JSONB as a dict; fall back to JSON parse if string
            metadata=r[4] if isinstance(r[4], dict) else json.loads(r[4] or "{}"),
            created_at=r[5],
        )
        for r in rows
    ]


def get_recent_messages_for_context(chat_id: int, n: int = 6) -> list[MessageRecord]:
    """Return the N most recent messages (for injecting context into next LLM call).

    Returned in chronological order (oldest first) so they read naturally.
    """
    ensure_history_schema()
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT id, chat_id, sender, message, metadata, created_at
            FROM stored_messages
            WHERE chat_id = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (chat_id, n),
        )
        rows = cur.fetchall()

    records = [
        MessageRecord(
            id=r[0],
            chat_id=r[1],
            sender=r[2],
            sender_label="user" if r[2] == SENDER_USER else "agent",
            message=r[3],
            metadata=r[4] if isinstance(r[4], dict) else json.loads(r[4] or "{}"),
            created_at=r[5],
        )
        for r in rows
    ]
    return list(reversed(records))  # oldest → newest
