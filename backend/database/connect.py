# backend/database/db.py
from __future__ import annotations

import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from functools import lru_cache
from typing import Final

import boto3
import psycopg2
from dotenv import load_dotenv
from psycopg2.extensions import connection as PGConnection
from psycopg2.extensions import cursor as PGCursor

# Load .env AFTER imports (ruff E402)
load_dotenv()

DEFAULT_SSLMODE: Final[str] = "verify-full"
DEFAULT_SSLROOTCERT: Final[str] = "certs/global-bundle.pem"
DEFAULT_PORT: Final[int] = 5432
DEFAULT_REGION: Final[str] = "us-east-1"


@dataclass(frozen=True)
class DBConfig:
    host: str
    port: int
    dbname: str
    user: str
    secret_arn: str
    region: str
    sslmode: str = DEFAULT_SSLMODE
    sslrootcert: str = DEFAULT_SSLROOTCERT


def _env(name: str, default: str | None = None) -> str:
    """
    Read an environment variable as a non-optional string.
    Raises a clear error if missing and no default is provided.
    """
    val = os.getenv(name)
    if val is not None and val != "":
        return val
    if default is not None:
        return default
    raise RuntimeError(f"Missing required environment variable: {name}")


def load_db_config() -> DBConfig:
    """
    Load database config from environment variables.
    """
    port_str = _env("DB_PORT", str(DEFAULT_PORT))

    return DBConfig(
        host=_env("DB_HOST"),
        port=int(port_str),
        dbname=_env("DB_NAME"),
        user=_env("DB_USER"),
        secret_arn=_env("DB_SECRET_ARN"),
        region=_env("AWS_REGION", DEFAULT_REGION),
        sslmode=_env("DB_SSLMODE", DEFAULT_SSLMODE),
        sslrootcert=_env("DB_SSLROOTCERT", DEFAULT_SSLROOTCERT),
    )


@lru_cache(maxsize=1)
def _get_db_password(secret_arn: str, region: str) -> str:
    """
    Fetch + cache the DB password from AWS Secrets Manager.
    Cache lasts for process lifetime; restart process to refresh.
    """
    sm = boto3.client("secretsmanager", region_name=region)
    secret_str = sm.get_secret_value(SecretId=secret_arn)["SecretString"]
    secret = json.loads(secret_str)

    password = secret.get("password")
    if not isinstance(password, str) or not password:
        raise RuntimeError("Secrets Manager secret did not contain a valid 'password' field.")
    return password


def get_conn(cfg: DBConfig | None = None) -> PGConnection:
    """
    Create a new psycopg2 connection.
    For a web app, switch to a connection pool (psycopg_pool / SQLAlchemy) soon.
    """
    cfg = cfg or load_db_config()
    password = _get_db_password(cfg.secret_arn, cfg.region)

    return psycopg2.connect(
        host=cfg.host,
        port=cfg.port,
        dbname=cfg.dbname,
        user=cfg.user,
        password=password,
        sslmode=cfg.sslmode,
        sslrootcert=cfg.sslrootcert,
    )


@contextmanager
def db_cursor(cfg: DBConfig | None = None) -> Iterator[PGCursor]:
    """
    Context manager that yields a cursor and handles commit/rollback/close safely.
    """
    conn: PGConnection | None = None
    try:
        conn = get_conn(cfg)
        cur = conn.cursor()
        yield cur
        conn.commit()
    except Exception:
        if conn is not None:
            conn.rollback()
        raise
    finally:
        if conn is not None:
            conn.close()


def smoke_test() -> None:
    """Quick connectivity test."""
    with db_cursor() as cur:
        cur.execute("SELECT version();")
        row = cur.fetchone()
        print(row[0] if row else "No result")


if __name__ == "__main__":
    smoke_test()
