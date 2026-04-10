import React, { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import ChatInterface, {
  ChatMessage,
  ChatReply,
} from "../components/ChatInterface";
import { StockChartData } from "../components/StockPriceChart";
import Navbar from "../components/Navbar";
import { getAgentApiBase } from "../lib/api";
import { clearAuthSession, getAuthToken, getStoredUser } from "../lib/auth";

type AssistantMode = "auto" | "housing" | "market";

const API_BASE_URL = getAgentApiBase();

const isAssistantMode = (value: string | null): value is AssistantMode =>
  value === "auto" || value === "housing" || value === "market";

const modeOptions = [
  { id: "auto", label: "Auto" },
  { id: "housing", label: "Housing" },
  { id: "market", label: "Market" },
];

const promptSets: Record<AssistantMode, string[]> = {
  auto: [
    "Compare median home values in Philadelphia, Austin, and Miami.",
    "What is the weather forecast in Austin, Texas this week?",
    "What is Apple current stock price?",
    "Which technology companies have strong buy ratings?",
  ],
  housing: [
    "What is the housing inventory in Austin Texas?",
    "What is the median home price in Philadelphia?",
    "Compare median home values in Philadelphia, Austin, and Miami.",
    "What is the weather forecast in Austin, Texas this week?",
  ],
  market: [
    "What is Apple current stock price?",
    "Tesla stock price and analyst recommendations.",
    "Which technology companies have strong buy ratings?",
    "What is the current unemployment rate?",
  ],
};

const modeContent: Record<
  AssistantMode,
  {
    title: string;
    subtitle: string;
    welcomeText: string;
    inputPlaceholder: string;
  }
> = {
  auto: {
    title: "One workspace for housing and markets",
    subtitle:
      "Ask city, housing, weather, stock, or macro questions in one thread. Auto mode chooses the right backend agent for you.",
    welcomeText:
      "Ask a question about U.S. cities, housing, weather, stocks, or broader market conditions.",
    inputPlaceholder:
      "Ask about housing, weather, city economics, stocks, or macro trends...",
  },
  housing: {
    title: "Pinned to housing and city analysis",
    subtitle:
      "Use this mode when you want the assistant to stay focused on U.S. housing, affordability, income, and weather.",
    welcomeText:
      "Housing mode is pinned. Ask about inventory, home values, rents, incomes, or weather in U.S. cities.",
    inputPlaceholder:
      "Ask about housing inventory, home values, rents, income, or weather...",
  },
  market: {
    title: "Pinned to stock and market analysis",
    subtitle:
      "Use this mode when you want tighter routing for equities, analyst recommendations, sector screens, and macro indicators.",
    welcomeText:
      "Market mode is pinned. Ask about stock prices, analyst sentiment, sectors, or macro indicators.",
    inputPlaceholder:
      "Ask about stock prices, analyst recommendations, sectors, or macro data...",
  },
};

const endpointByMode: Record<AssistantMode, string> = {
  auto: "/api/chat",
  housing: "/api/chat/housing",
  market: "/api/chat/market",
};

interface ChatSummary {
  id: number | string;
  agent_type?: string | null;
  title?: string | null;
  created_at: string;
}

interface HistoryMessage {
  id: number;
  sender: "user" | "agent";
  message: string;
  metadata?: {
    chart_data?: StockChartData | null;
    [key: string]: unknown;
  };
  created_at: string;
}

interface ChatHistoryResponse {
  chat_id: number;
  agent_type?: string | null;
  title?: string | null;
  messages: HistoryMessage[];
}

interface LocalChatRecord {
  id: number | string;
  agent_type?: string | null;
  title?: string | null;
  created_at: string;
  messages: HistoryMessage[];
}

const toAgentType = (
  value: string | null | undefined,
): "housing" | "market" | null => {
  if (value === "housing" || value === "market") {
    return value;
  }
  return null;
};

const localHistoryKey = (userId: number | undefined) =>
  `virtual_economist_local_history:${userId ?? "guest"}`;

const readLocalHistory = (userId: number | undefined): LocalChatRecord[] => {
  const raw = localStorage.getItem(localHistoryKey(userId));
  if (!raw) {
    return [];
  }

  try {
    const parsed = JSON.parse(raw) as LocalChatRecord[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    localStorage.removeItem(localHistoryKey(userId));
    return [];
  }
};

const writeLocalHistory = (userId: number | undefined, chats: LocalChatRecord[]) => {
  localStorage.setItem(localHistoryKey(userId), JSON.stringify(chats));
};

const AssistantWorkspace: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const modeParam = searchParams.get("mode");
  const activeMode: AssistantMode = isAssistantMode(modeParam)
    ? modeParam
    : "auto";
  const [conversationViewKey, setConversationViewKey] = useState(0);
  const [chatSummaries, setChatSummaries] = useState<ChatSummary[]>([]);
  const [selectedChatId, setSelectedChatId] = useState<number | string | null>(null);
  const [seedMessages, setSeedMessages] = useState<ChatMessage[]>([]);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);
  const [isChatListLoading, setIsChatListLoading] = useState(false);
  const [authState, setAuthState] = useState(() => ({
    token: getAuthToken(),
    user: getStoredUser(),
  }));

  useEffect(() => {
    const syncAuth = () => {
      setAuthState({
        token: getAuthToken(),
        user: getStoredUser(),
      });
    };

    window.addEventListener("storage", syncAuth);
    window.addEventListener("auth-changed", syncAuth);

    return () => {
      window.removeEventListener("storage", syncAuth);
      window.removeEventListener("auth-changed", syncAuth);
    };
  }, []);

  const isAuthenticated = Boolean(authState.token && authState.user);

  const handleModeChange = (nextMode: string) => {
    if (!isAssistantMode(nextMode)) {
      return;
    }

    const nextSearchParams = new URLSearchParams(searchParams);

    if (nextMode === "auto") {
      nextSearchParams.delete("mode");
    } else {
      nextSearchParams.set("mode", nextMode);
    }

    setSearchParams(nextSearchParams);
  };

  const loadChatSummaries: () => Promise<void> = useCallback(async () => {
    if (!authState.token) {
      setChatSummaries(
        readLocalHistory(authState.user?.id).map(({ id, agent_type, title, created_at }) => ({
          id,
          agent_type,
          title,
          created_at,
        })),
      );
      return;
    }

    setIsChatListLoading(true);
    setHistoryError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/history/chats?limit=20`, {
        headers: {
          Authorization: `Bearer ${authState.token}`,
        },
      });

      if (!response.ok) {
        if (response.status === 401) {
          clearAuthSession();
          throw new Error("Your session expired. Log in again to load saved chats.");
        }
        throw new Error("Unable to load saved chats.");
      }

      const data = (await response.json()) as ChatSummary[];
      setChatSummaries(data);
    } catch (error) {
      const localChats = readLocalHistory(authState.user?.id).map(
        ({ id, agent_type, title, created_at }) => ({
          id,
          agent_type,
          title,
          created_at,
        }),
      );
      setChatSummaries(localChats);
      setHistoryError(
        localChats.length > 0
          ? "Database unavailable. Showing chats saved in this browser."
          : error instanceof Error
            ? error.message
            : "Unable to load saved chats.",
      );
    } finally {
      setIsChatListLoading(false);
    }
  }, [authState.token, authState.user?.id]);

  useEffect(() => {
    if (!authState.token) {
      setChatSummaries([]);
      setSelectedChatId(null);
      setSeedMessages([]);
      setHistoryError(null);
      return;
    }

    void loadChatSummaries();
  }, [authState.token, loadChatSummaries]);

  const loadConversation = async (chat: ChatSummary) => {
    setConversationViewKey((previous) => previous + 1);

    if (typeof chat.id === "string") {
      const localChat = readLocalHistory(authState.user?.id).find(
        (entry) => entry.id === chat.id,
      );
      setSelectedChatId(chat.id);
      setSeedMessages(
        (localChat?.messages || []).map((message) => ({
          id: `history-${message.id}`,
          sender: message.sender === "user" ? "user" : "assistant",
          text: message.message,
          agentType:
            message.sender === "agent" ? toAgentType(localChat?.agent_type) : undefined,
          chartData:
            message.sender === "agent"
              ? (message.metadata?.chart_data ?? null)
              : null,
        })),
      );
      return;
    }

    if (!authState.token) {
      return;
    }

    setSelectedChatId(chat.id);
    setIsHistoryLoading(true);
    setHistoryError(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/history/chats/${chat.id}/messages`,
        {
          headers: {
            Authorization: `Bearer ${authState.token}`,
          },
        },
      );

      if (!response.ok) {
        if (response.status === 401) {
          clearAuthSession();
          throw new Error(
            "Your session expired. Log in again to reopen saved conversations.",
          );
        }
        throw new Error("Unable to load that conversation.");
      }

      const data = (await response.json()) as ChatHistoryResponse;
      setSeedMessages(
        data.messages.map((message) => ({
          id: `history-${message.id}`,
          sender: message.sender === "user" ? "user" : "assistant",
          text: message.message,
          agentType:
            message.sender === "agent" ? toAgentType(data.agent_type) : undefined,
          chartData:
            message.sender === "agent"
              ? (message.metadata?.chart_data ?? null)
              : null,
        })),
      );
    } catch (error) {
      const localChat = readLocalHistory(authState.user?.id).find(
        (entry) => entry.id === chat.id,
      );
      if (localChat) {
        setSeedMessages(
          localChat.messages.map((message) => ({
            id: `history-${message.id}`,
            sender: message.sender === "user" ? "user" : "assistant",
            text: message.message,
            agentType:
              message.sender === "agent"
                ? toAgentType(localChat.agent_type)
                : undefined,
            chartData:
              message.sender === "agent"
                ? (message.metadata?.chart_data ?? null)
                : null,
          })),
        );
      } else {
        setSeedMessages([]);
      }
      setHistoryError(
        localChat
          ? "Database unavailable. Loaded the browser-saved copy of this chat."
          : error instanceof Error
            ? error.message
            : "Unable to load that conversation.",
      );
    } finally {
      setIsHistoryLoading(false);
    }
  };

  const handleSendMessage = async (
    message: string,
    conversationId: number | string | null,
  ): Promise<ChatReply> => {
    const requestBody = typeof conversationId === "number"
      ? { question: message, conversation_id: conversationId }
      : { question: message };

    const response = await fetch(
      `${API_BASE_URL}${endpointByMode[activeMode]}`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(authState.token
            ? { Authorization: `Bearer ${authState.token}` }
            : {}),
        },
        body: JSON.stringify(requestBody),
      },
    );

    let payload: Record<string, unknown> | null = null;

    try {
      payload = (await response.json()) as Record<string, unknown>;
    } catch {
      payload = null;
    }

    if (!response.ok) {
      if (response.status === 401) {
        clearAuthSession();
        throw new Error("Your session expired. Log in again to save chats.");
      }
      const detail =
        (payload?.error as string | undefined) ||
        (payload?.detail as string | undefined) ||
        `Request failed with status ${response.status}.`;

      throw new Error(
        `${detail} Check that the backend is running on ${API_BASE_URL}.`,
      );
    }

    return {
      answer:
        typeof payload?.answer === "string"
          ? payload.answer
          : "I couldn't generate a reliable answer.",
      agent_type:
        payload?.agent_type === "housing" || payload?.agent_type === "market"
          ? payload.agent_type
          : payload?.agent_type === null
            ? null
            : undefined,
      conversation_id:
        typeof payload?.conversation_id === "string" ||
        typeof payload?.conversation_id === "number" ||
        payload?.conversation_id === null
          ? (payload.conversation_id as string | number | null)
          : null,
      error:
        typeof payload?.error === "string" || payload?.error === null
          ? (payload.error as string | null)
          : null,
      tool_trace:
        payload && Array.isArray(payload.tool_trace) ? payload.tool_trace : null,
      chart_data:
        payload?.chart_data && typeof payload.chart_data === "object"
          ? (payload.chart_data as StockChartData)
          : null,
    };
  };

  const persistLocalTurn = (
    question: string,
    reply: ChatReply,
    conversationId: number | string | null,
  ) => {
    const userId = authState.user?.id;
    const chats = readLocalHistory(userId);
    const chatId =
      reply.conversation_id ??
      conversationId ??
      `local-${Date.now()}`;
    const existing = chats.find((chat) => chat.id === chatId);
    const createdAt = existing?.created_at || new Date().toISOString();
    const answerText =
      reply.answer?.trim() ||
      reply.error?.trim() ||
      "I couldn't generate a reliable answer.";

    const nextMessages = [
      ...(existing?.messages || []),
      {
        id: Date.now(),
        sender: "user" as const,
        message: question,
        metadata: {},
        created_at: new Date().toISOString(),
      },
      {
        id: Date.now() + 1,
        sender: "agent" as const,
        message: answerText,
        metadata: {
          chart_data: reply.chart_data ?? null,
        },
        created_at: new Date().toISOString(),
      },
    ];

    const nextRecord: LocalChatRecord = {
      id: chatId,
      agent_type:
        Object.prototype.hasOwnProperty.call(reply, "agent_type")
          ? (reply.agent_type ?? null)
          : (existing?.agent_type ?? null),
      title: existing?.title || `${question.slice(0, 60)}${question.length > 60 ? "…" : ""}`,
      created_at: createdAt,
      messages: nextMessages,
    };

    const nextChats = [
      nextRecord,
      ...chats.filter((chat) => chat.id !== chatId),
    ].slice(0, 20);

    writeLocalHistory(userId, nextChats);
    setChatSummaries(
      nextChats.map(({ id, agent_type, title, created_at }) => ({
        id,
        agent_type,
        title,
        created_at,
      })),
    );

    return chatId;
  };

  const handleReply = (reply: ChatReply) => {
    if (reply.conversation_id != null && selectedChatId !== reply.conversation_id) {
      setSelectedChatId(reply.conversation_id);
    }

    if (authState.token) {
      void loadChatSummaries();
    }
  };

  const handleSendWithPersistence = async (
    message: string,
    conversationId: number | string | null,
  ): Promise<ChatReply> => {
    const reply = await handleSendMessage(message, conversationId);
    const persistedConversationId = persistLocalTurn(message, reply, conversationId);
    return {
      ...reply,
      conversation_id: reply.conversation_id ?? persistedConversationId,
    };
  };

  const handleResetConversation = () => {
    setConversationViewKey((previous) => previous + 1);
    setSelectedChatId(null);
    setSeedMessages([]);
    setHistoryError(null);
  };

  return (
    <>
      <Navbar />
      <main className="assistant-page">
        <div className="assistant-layout">
          <aside className="history-sidebar">
            <div className="history-sidebar-header">
              <div>
                <p className="history-sidebar-eyebrow">Workspace</p>
                <h2>Saved chats</h2>
              </div>

              {isAuthenticated ? (
                <button
                  type="button"
                  className="history-refresh-button"
                  onClick={() => void loadChatSummaries()}
                >
                  Refresh
                </button>
              ) : null}
            </div>

            {isAuthenticated && authState.user ? (
              <div className="history-user-card">
                <p className="history-user-label">Signed in</p>
                <strong>{authState.user.username}</strong>
                <span>{authState.user.email}</span>
              </div>
            ) : (
              <div className="history-login-card">
                <p className="history-user-label">Save your work</p>
                <strong>Sign in for persistent chat history.</strong>
                <span>
                  Guests can still chat, but conversations will not be saved.
                </span>
                <div className="history-login-actions">
                  <Link className="history-primary-link" to="/login">
                    Log in
                  </Link>
                  <Link className="history-secondary-link" to="/signup">
                    Sign up
                  </Link>
                </div>
              </div>
            )}

            {historyError ? (
              <p className="history-error-text">{historyError}</p>
            ) : null}

            <div className="history-list">
              {isAuthenticated && isChatListLoading ? (
                <p className="history-empty-text">Loading saved chats…</p>
              ) : null}

              {isAuthenticated && !isChatListLoading && chatSummaries.length === 0 ? (
                <p className="history-empty-text">
                  No saved chats yet. Your next message will create one.
                </p>
              ) : null}

              {chatSummaries.map((chat) => (
                <button
                  key={chat.id}
                  type="button"
                  className={`history-item ${
                    selectedChatId === chat.id ? "active" : ""
                  }`}
                  onClick={() => void loadConversation(chat)}
                >
                  <span className="history-item-badge">
                    {toAgentType(chat.agent_type) === "housing"
                      ? "Housing"
                      : toAgentType(chat.agent_type) === "market"
                        ? "Market"
                        : "Scope"}
                  </span>
                  <strong>{chat.title || "Untitled chat"}</strong>
                  <span>{new Date(chat.created_at).toLocaleString()}</span>
                </button>
              ))}
            </div>
          </aside>

          <div className="assistant-main">
            {isHistoryLoading ? (
              <div className="history-loading-banner">
                Loading conversation…
              </div>
            ) : null}

            <ChatInterface
              title={modeContent[activeMode].title}
              subtitle={modeContent[activeMode].subtitle}
              welcomeText={modeContent[activeMode].welcomeText}
              inputPlaceholder={modeContent[activeMode].inputPlaceholder}
              sessionKey={`${activeMode}:${conversationViewKey}`}
              examplePrompts={promptSets[activeMode]}
              modeOptions={modeOptions}
              activeMode={activeMode}
              initialMessages={seedMessages}
              initialConversationId={selectedChatId}
              onModeChange={handleModeChange}
              onResetConversation={handleResetConversation}
              onReply={handleReply}
              onSendMessage={handleSendWithPersistence}
            />
          </div>
        </div>
      </main>
    </>
  );
};

export default AssistantWorkspace;
