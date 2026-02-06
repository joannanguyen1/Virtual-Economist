import React, { useEffect, useState, useRef } from "react";
import ReactMarkdown from "react-markdown";
import rehypeRaw from "rehype-raw";
import rehypeSanitize from "rehype-sanitize";
import "./ChatDisplay.css";

export interface Message {
  sender: "user" | "chatbot";
  content: string;
  isTyping?: boolean;
}

interface ChatDisplayProps {
  messages: Message[];
  activeChat: number | null;
}

function areMessagesEqual(a: Message[], b: Message[]) {
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) {
    if (
      a[i].sender !== b[i].sender ||
      a[i].content !== b[i].content
    ) {
      return false;
    }
  }
  return true;
}

const ChatDisplay: React.FC<ChatDisplayProps> = ({ messages, activeChat }) => {
  const [displayedMessages, setDisplayedMessages] = useState<Message[]>([]);
  const previousMessagesLength = useRef(messages.length);
  const lastActiveChat = useRef<number | null>(activeChat);
  const isInitialLoad = useRef(true);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (lastActiveChat.current !== activeChat) {
      setDisplayedMessages(messages.map(msg => ({ ...msg, isTyping: false })));
      lastActiveChat.current = activeChat;
      previousMessagesLength.current = messages.length;
      isInitialLoad.current = false;
      return;
    }

    if (isInitialLoad.current) {
      setDisplayedMessages(messages.map(msg => ({
        ...msg,
        isTyping: false
      })));
      isInitialLoad.current = false;
      previousMessagesLength.current = messages.length;
      return;
    }

    const isAppend =
      messages.length === displayedMessages.length + 1 &&
      areMessagesEqual(
        displayedMessages,
        messages.slice(0, displayedMessages.length)
      );

    const lastMessage = messages[messages.length - 1];

    if (
      isAppend &&
      lastMessage?.sender === "chatbot"
    ) {
      setDisplayedMessages(prev => [
        ...prev,
        { ...lastMessage, content: "", isTyping: true }
      ]);

      let currentText = "";
      const interval = setInterval(() => {
        currentText = lastMessage.content.slice(0, currentText.length + 1);
        setDisplayedMessages(prev => {
          const newMessages = [...prev];
          newMessages[newMessages.length - 1] = {
            ...lastMessage,
            content: currentText,
            isTyping: true
          };
          return newMessages;
        });

        if (currentText.length === lastMessage.content.length) {
          clearInterval(interval);
          setDisplayedMessages(prev => {
            const newMessages = [...prev];
            newMessages[newMessages.length - 1] = {
              ...lastMessage,
              isTyping: false
            };
            return newMessages;
          });
        }
      }, 10);

      previousMessagesLength.current = messages.length;
      return () => clearInterval(interval);
    } else {
      setDisplayedMessages(messages.map(msg => ({
        ...msg,
        isTyping: false
      })));
      previousMessagesLength.current = messages.length;
    }
  }, [messages, activeChat]);

  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "auto" });
    }
  }, [displayedMessages, activeChat]);

  return (
    <div className="chat-display">
      {displayedMessages.map((msg, index) => (
        <div key={index} className={`chat-message ${msg.sender}`}>
          {msg.sender === "chatbot" ? (
            <ReactMarkdown
              rehypePlugins={[rehypeRaw, rehypeSanitize]}
              components={{
                p: ({ children }) => <p style={{ margin: 0 }}>{children}</p>
              }}
            >
              {msg.content}
            </ReactMarkdown>
          ) : (
            msg.content
          )}
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
};

export default ChatDisplay;
