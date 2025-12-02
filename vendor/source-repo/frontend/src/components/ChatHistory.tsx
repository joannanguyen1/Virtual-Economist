import React from "react";
import "./ChatHistory.css";

interface Message {
  sender: "user" | "chatbot";
  content: string;
}

export interface ChatSession {
  id: number;
  timestamp: string;
  messages: Message[];
  title?: string;
}

export interface ChatHistoryProps {
  history: ChatSession[];
  onSelectChat: (id: number) => void;
  onNewChat: () => void;
  onDeleteChat: (id: number) => void;
  activeChat: number | null;
}

const ChatHistory: React.FC<ChatHistoryProps> = ({
  history,
  onSelectChat,
  onNewChat,
  onDeleteChat,
  activeChat
}) => {
  const getChatTitle = (chat: ChatSession) => {
    if (chat.title) return chat.title;
    const firstUserMessage = chat.messages.find(msg => msg.sender === "user");
    return firstUserMessage
      ? firstUserMessage.content.slice(0, 30) + "..."
      : chat.timestamp;
  };

  return (
    <div className="chat-history">
      
        <button className="new-chat-button" onClick={onNewChat}>
          + New Chat
        </button>
    

      <div className="history-list">
        {history.length === 0 ? (
          <p className="empty-history">No chat history yet</p>
        ) : (
          history.map(chat => (
            <div
              key={chat.id}
              className={`history-item ${activeChat === chat.id ? "active" : ""}`}
            >
              <div
                className="history-item-content"
                onClick={() => onSelectChat(chat.id)}
              >
                <p className="chat-title">{getChatTitle(chat)}</p>
                <p className="chat-timestamp">{chat.timestamp}</p>
              </div>
              <button
                className="delete-chat-button"
                onClick={e => {
                  e.stopPropagation();
                  onDeleteChat(chat.id);
                }}
              >
                ×
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default ChatHistory;
