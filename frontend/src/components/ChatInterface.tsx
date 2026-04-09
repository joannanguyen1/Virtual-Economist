import React, { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import "../styles/chat.css";

type AgentType = "housing" | "market" | null;

export interface ChatMessage {
  id: string;
  sender: "user" | "assistant";
  text: string;
  agentType?: AgentType;
}

interface ModeOption {
  id: string;
  label: string;
}

export interface ChatReply {
  answer: string;
  agent_type?: AgentType;
  conversation_id?: number | string | null;
  error?: string | null;
  tool_trace?: unknown[] | null;
}

interface ChatInterfaceProps {
  title: string;
  subtitle: string;
  welcomeText: string;
  inputPlaceholder: string;
  sessionKey: string;
  examplePrompts?: string[];
  modeOptions?: ModeOption[];
  activeMode?: string;
  onModeChange?: (mode: string) => void;
  initialMessages?: ChatMessage[];
  initialConversationId?: number | string | null;
  onResetConversation?: () => void;
  onReply?: (reply: ChatReply) => void;
  onSendMessage: (
    message: string,
    conversationId: number | string | null,
  ) => Promise<ChatReply>;
}

const createWelcomeMessage = (text: string): ChatMessage => ({
  id: `welcome-${Date.now()}`,
  sender: "assistant",
  text,
});

const formatAgentLabel = (agentType: AgentType) => {
  if (agentType === "housing") return "Housing";
  if (agentType === "market") return "Market";
  return "Scope";
};

const ChatInterface: React.FC<ChatInterfaceProps> = ({
  title,
  subtitle,
  welcomeText,
  inputPlaceholder,
  sessionKey,
  examplePrompts = [],
  modeOptions = [],
  activeMode,
  onModeChange,
  initialMessages,
  initialConversationId = null,
  onResetConversation,
  onReply,
  onSendMessage,
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>(
    initialMessages?.length ? initialMessages : [createWelcomeMessage(welcomeText)],
  );
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<
    number | string | null
  >(initialConversationId);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const previousSessionKeyRef = useRef(sessionKey);

  useEffect(() => {
    if (
      previousSessionKeyRef.current === sessionKey &&
      (!initialMessages || initialMessages.length === 0)
    ) {
      return;
    }

    previousSessionKeyRef.current = sessionKey;
    setMessages(
      initialMessages?.length ? initialMessages : [createWelcomeMessage(welcomeText)],
    );
    setConversationId(initialConversationId);
    setInputValue("");
  }, [initialConversationId, initialMessages, sessionKey, welcomeText]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  useEffect(() => {
    const textarea = textareaRef.current;

    if (!textarea) {
      return;
    }

    textarea.style.height = "0px";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 180)}px`;
  }, [inputValue]);

  const resetConversation = () => {
    setMessages([createWelcomeMessage(welcomeText)]);
    setConversationId(null);
    setInputValue("");
    setIsLoading(false);
    onResetConversation?.();
  };

  const submitMessage = async (rawMessage: string) => {
    const trimmedMessage = rawMessage.trim();

    if (!trimmedMessage || isLoading) {
      return;
    }

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: "user",
      text: trimmedMessage,
    };

    setMessages((previous) => [...previous, userMessage]);
    setInputValue("");
    setIsLoading(true);

    try {
      const reply = await onSendMessage(trimmedMessage, conversationId);
      const answer =
        reply.answer?.trim() ||
        reply.error?.trim() ||
        "I couldn't generate a reliable answer for that request.";

      setConversationId(reply.conversation_id ?? null);
      onReply?.(reply);

      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        sender: "assistant",
        text: answer,
        agentType:
          Object.prototype.hasOwnProperty.call(reply, "agent_type")
            ? (reply.agent_type ?? null)
            : undefined,
      };

      setMessages((previous) => [...previous, assistantMessage]);
    } catch (error) {
      const fallbackMessage =
        error instanceof Error
          ? error.message
          : "I couldn't reach the backend. Make sure it is running on http://localhost:8000.";

      setMessages((previous) => [
        ...previous,
        {
          id: `assistant-error-${Date.now()}`,
          sender: "assistant",
          text: fallbackMessage,
          agentType: null,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    await submitMessage(inputValue);
  };

  const handleKeyDown = async (
    event: React.KeyboardEvent<HTMLTextAreaElement>,
  ) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      await submitMessage(inputValue);
    }
  };

  return (
    <div className="assistant-shell">
      <section className="assistant-hero">
        <div className="assistant-hero-copy">
          <p className="assistant-eyebrow">Virtual Economist</p>
          <h1>{title}</h1>
          <p className="assistant-subtitle">{subtitle}</p>
        </div>

        <div className="assistant-hero-actions">
          {modeOptions.length > 0 && onModeChange ? (
            <div className="assistant-mode-switcher" aria-label="Agent mode">
              {modeOptions.map((mode) => (
                <button
                  key={mode.id}
                  type="button"
                  className={`mode-pill ${
                    activeMode === mode.id ? "active" : ""
                  }`}
                  onClick={() => onModeChange(mode.id)}
                >
                  {mode.label}
                </button>
              ))}
            </div>
          ) : null}

          <button
            type="button"
            className="secondary-action-button"
            onClick={resetConversation}
          >
            New chat
          </button>
        </div>
      </section>

      {examplePrompts.length > 0 ? (
        <section className="assistant-prompt-grid">
          {examplePrompts.map((prompt) => (
            <button
              key={prompt}
              type="button"
              className="prompt-card"
              onClick={() => void submitMessage(prompt)}
              disabled={isLoading}
            >
              {prompt}
            </button>
          ))}
        </section>
      ) : null}

      <section className="chat-container">
        <div className="chat-toolbar">
          <div>
            <p className="chat-toolbar-label">Conversation</p>
            <h2>Ask naturally. The backend handles routing and data lookups.</h2>
          </div>
        </div>

        <div className="chat-messages">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`message-row ${
                message.sender === "user" ? "user" : "assistant"
              }`}
            >
              <article
                className={`message ${
                  message.sender === "user" ? "user" : "assistant"
                }`}
              >
                {message.sender === "assistant" &&
                message.agentType !== undefined ? (
                  <p className="message-label">
                    {formatAgentLabel(message.agentType)}
                  </p>
                ) : null}

                <div className="message-body">
                  {message.sender === "assistant" ? (
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {message.text}
                    </ReactMarkdown>
                  ) : (
                    <p>{message.text}</p>
                  )}
                </div>
              </article>
            </div>
          ))}

          {isLoading ? (
            <div className="message-row assistant">
              <article className="message assistant typing-message">
                <p className="message-label">Working</p>
                <div className="typing-indicator" aria-label="Thinking">
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                </div>
              </article>
            </div>
          ) : null}

          <div ref={messagesEndRef} />
        </div>

        <form className="input-area" onSubmit={handleSubmit}>
          <label className="composer-label" htmlFor="assistant-input">
            Message
          </label>

          <div className="composer">
            <textarea
              id="assistant-input"
              ref={textareaRef}
              className="chat-input"
              placeholder={inputPlaceholder}
              value={inputValue}
              onChange={(event) => setInputValue(event.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
              rows={1}
            />

            <button
              type="submit"
              className="send-button"
              disabled={isLoading || !inputValue.trim()}
            >
              Send
            </button>
          </div>
        </form>
      </section>
    </div>
  );
};

export default ChatInterface;
