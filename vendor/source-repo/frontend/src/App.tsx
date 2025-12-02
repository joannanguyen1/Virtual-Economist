import React, { useState, useEffect } from "react";
import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
import LoginPage from "./components/LoginPage";
import SignupPage from "./components/SignUpPage";
import ForgotPasswordPage from "./components/ForgotPasswordPage";
import ChatHistory from "./components/ChatHistory";
import ChatDisplay from "./components/ChatDisplay";
import { Message } from "./components/ChatDisplay";
import { ChatSession } from "./components/ChatHistory";
import ChatInput from "./components/ChatInput";
import { User } from "./components/LoginPage";
import "./App.css";

const agents = ["Stock Agent", "Housing Agent"];

const App: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>(() => {
    try {
      if (!user) {
        const savedMessages = sessionStorage.getItem('guestMessages');
        return savedMessages ? JSON.parse(savedMessages) : [];
      }
      const savedMessages = localStorage.getItem('messages');
      return savedMessages ? JSON.parse(savedMessages) : [];
    } catch (error) {
      console.error('Error parsing messages:', error);
      return [];
    }
  });
  const [isLoading, setIsLoading] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [inputValue, setInputValue] = useState<string>("");
  const [user, setUser] = useState<User | null>(() => {
    const token = localStorage.getItem("token");
    return token ? { id: "", email: "", username: "" } : null;
  });

  const [history, setHistory] = useState<ChatSession[]>(() => {
    try {
      if (!user) {
        const savedHistory = sessionStorage.getItem('guestHistory');
        return savedHistory ? JSON.parse(savedHistory) : [];
      }
      const savedHistory = localStorage.getItem('chatHistory');
      return savedHistory ? JSON.parse(savedHistory) : [];
    } catch (error) {
      console.error('Error parsing chat history:', error);
      return [];
    }
  });
  const [activeChat, setActiveChat] = useState<number | null>(() => {
    try {
      if (!user) {
        const savedActiveChat = sessionStorage.getItem('guestActiveChat');
        return savedActiveChat ? JSON.parse(savedActiveChat) : null;
      }
      const savedActiveChat = localStorage.getItem('activeChat');
      return savedActiveChat ? JSON.parse(savedActiveChat) : null;
    } catch (error) {
      console.error('Error parsing active chat:', error);
      return null;
    }
  });
  const [isHistoryLoaded, setIsHistoryLoaded] = useState(false);
  const [historyCollapsed, setHistoryCollapsed] = useState(false);

  useEffect(() => {
    try {
      if (!user) {
        sessionStorage.setItem('guestHistory', JSON.stringify(history));
      } else {
        localStorage.setItem('chatHistory', JSON.stringify(history));
      }
    } catch (error) {
      console.error('Error saving chat history:', error);
    }
  }, [history, user]);

  useEffect(() => {
    try {
      if (!user) {
        sessionStorage.setItem('guestActiveChat', JSON.stringify(activeChat));
      } else {
        localStorage.setItem('activeChat', JSON.stringify(activeChat));
      }
    } catch (error) {
      console.error('Error saving active chat:', error);
    }
  }, [activeChat, user]);

  useEffect(() => {
    try {
      if (!user) {
        sessionStorage.setItem('guestMessages', JSON.stringify(messages));
      } else {
        localStorage.setItem('messages', JSON.stringify(messages));
      }
    } catch (error) {
      console.error('Error saving messages:', error);
    }
  }, [messages, user]);

  useEffect(() => {
    const loadChatHistory = async () => {
      try {
        const token = localStorage.getItem("token");
        const headers: HeadersInit = { "Content-Type": "application/json" };
        if (token) headers["Authorization"] = `Bearer ${token}`;

        const response = await fetch(
          "http://localhost:8000/chatHistory/history",
          { headers }
        );

        if (response.ok) {
          const sessions = await response.json();
          const formattedSessions = sessions.map((session: any) => ({
            id: session.chat_id,
            timestamp: session.started_at
              ? new Date(session.started_at).toLocaleString()
              : "Unknown Date",
            messages: session.messages.map((msg: any) => ({
              sender: msg.is_client ? "user" : "chatbot",
              content: msg.message,
            })),
          }));
          setHistory(formattedSessions);
        }
      } catch (error) {
        console.error("Error loading chat history:", error);
      }
      setIsHistoryLoaded(true);
    };

    loadChatHistory();
  }, [user]);

  const createNewChat = async (): Promise<number | null> => {
    try {
      const token = localStorage.getItem("token");
      const headers: HeadersInit = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const response = await fetch(
        "http://localhost:8000/chatHistory/create",
        {
          method: "POST",
          headers,
        }
      );

      let newChat: ChatSession;
      
      if (response.ok) {
        const newSession = await response.json();
        newChat = {
          id: newSession.chat_id,
          timestamp: new Date(newSession.started_at).toLocaleString(),
          messages: [],
        };
      } else {
        const tempId = Date.now();
        newChat = {
          id: tempId,
          timestamp: new Date().toLocaleString(),
          messages: [],
        };
      }

      setHistory([newChat, ...history]);
      setActiveChat(newChat.id);
      setMessages([]);
      setInputValue("");

      return newChat.id;
    } catch (error) {
      console.error("Error creating new chat:", error);
      const tempId = Date.now();
      const newChat: ChatSession = {
        id: tempId,
        timestamp: new Date().toLocaleString(),
        messages: [],
      };
      setHistory([newChat, ...history]);
      setActiveChat(tempId);
      setMessages([]);
      setInputValue("");
      return tempId;
    }
  };

  const handleDeleteChat = async (id: number) => {
    try {
      const token = localStorage.getItem("token");
      const headers: HeadersInit = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const response = await fetch(`http://localhost:8000/chatHistory/history/${id}`, {
        method: "DELETE",
        headers,
      });

      if (response.ok) {
        setHistory(history.filter((chat) => chat.id !== id));
        if (activeChat === id) {
          setActiveChat(null);
          setMessages([]);
        }
      }
    } catch (error) {
      console.error("Error deleting chat:", error);
    }
  };

  const handleLogin = (userData: User) => {
    sessionStorage.removeItem('guestHistory');
    sessionStorage.removeItem('guestActiveChat');
    sessionStorage.removeItem('guestMessages');

    setUser(userData);
    localStorage.setItem("user", JSON.stringify(userData));
  };

  const handleLogout = async () => {
    try {
      const token = localStorage.getItem("token");
      if (token) {
        await fetch("http://localhost:8000/auth/logout", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ token }),
        });
      }
    } catch (error) {
      console.error("Error during logout:", error);
    } finally {
      sessionStorage.clear();
      localStorage.removeItem("user");
      localStorage.removeItem("token");
      localStorage.removeItem("chatHistory");
      localStorage.removeItem("activeChat");
      localStorage.removeItem("messages");
      
      setUser(null);
      setHistory([]);
      setActiveChat(null);
      setMessages([]);
    }
  };

  const handleSelectChat = async (id: number) => {
    setActiveChat(id);
    const chatFromHistory = history.find(chat => chat.id === id);
    if (chatFromHistory) {
      setMessages(chatFromHistory.messages);
      return;
    }

    try {
      const token = localStorage.getItem("token");
      const headers: HeadersInit = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const response = await fetch(
        `http://localhost:8000/chatHistory/history/${id}`,
        { headers }
      );
      
      if (response.ok) {
        const chatData = await response.json();
        const formattedMessages: Message[] = chatData.messages.map((msg: any) => ({
          sender: msg.is_client ? "user" : "chatbot",
          content: msg.message,
        }));
        setMessages(formattedMessages);
        
        setHistory(prevHistory => 
          prevHistory.map(chat => 
            chat.id === id 
              ? { ...chat, messages: formattedMessages }
              : chat
          )
        );
      }
    } catch (error) {
      console.error("Error loading chat messages:", error);
    }
  };

  const handleSendMessage = async (message: string) => {
    if (!message.trim()) return;

    let currentChatId = activeChat;

    if (!currentChatId) {
      const createdChatId = await createNewChat();
      if (!createdChatId) return;
      currentChatId = createdChatId;
      setActiveChat(createdChatId);
    }

    const newMessage: Message = { sender: "user", content: message };
    const updated: Message[] = [...messages, newMessage];
    setMessages(updated);
    setInputValue("");

    setHistory(prevHistory => 
      prevHistory.map(chat => 
        chat.id === currentChatId 
          ? { ...chat, messages: updated }
          : chat
      )
    );

    if (!selectedAgent) {
      const botMessage: Message = { sender: "chatbot", content: "Please select an agent first." };
      const finalMessages: Message[] = [...updated, botMessage];
      setMessages(finalMessages);
      
      setHistory(prevHistory => 
        prevHistory.map(chat => 
          chat.id === currentChatId 
            ? { ...chat, messages: finalMessages }
            : chat
        )
      );
      return;
    }

    const agentSelection = {
      housingAgent: selectedAgent === "Housing Agent",
      stockAgent: selectedAgent === "Stock Agent",
    };

    setIsLoading(true);
    try {
      const token = localStorage.getItem("token");
      const headers: HeadersInit = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const response = await fetch("http://localhost:8000/api", {
        method: "POST",
        headers,
        body: JSON.stringify({
          question: message,
          agentSelection,
          chatId: currentChatId,
        }),
      });

      if (!response.ok) {
        if (response.status === 401) {
          handleLogout();
          throw new Error("Session expired. Please log in again.");
        }
        throw new Error("Failed to fetch response from the server");
      }

      const data = await response.json();
      const botMessage: Message = { sender: "chatbot", content: data.answer || "I didn't understand that." };
      const finalMessages: Message[] = [...updated, botMessage];
      setMessages(finalMessages);
      
      setHistory(prevHistory => 
        prevHistory.map(chat => 
          chat.id === currentChatId 
            ? { ...chat, messages: finalMessages }
            : chat
        )
      );
    } catch (error) {
      console.error("Error sending message:", error);
      const errorMessage: Message = { sender: "chatbot", content: "Sorry, I encountered an error. Please try again." };
      const finalMessages: Message[] = [...updated, errorMessage];
      setMessages(finalMessages);
      
      setHistory(prevHistory => 
        prevHistory.map(chat => 
          chat.id === currentChatId 
            ? { ...chat, messages: finalMessages }
            : chat
        )
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Router>
      <div className="app-container">
        <div className="top-nav">
          <div className="header-left">
            <Link to="/" className="home-button">
              Home
            </Link>
            <button
              onClick={() => setHistoryCollapsed(!historyCollapsed)}
              className="home-button header-collapse-button"
            >
              {historyCollapsed ? "Show History" : "Hide History"}
            </button>
          </div>
          <div className="header-title">
            Virtual Economist
          </div>
          {user ? (
            <button onClick={handleLogout} className="login-button">
              Logout
            </button>
          ) : (
            <Link to="/login" className="login-button">
              Login
            </Link>
          )}
        </div>

        <Routes>
          <Route
            path="/"
            element={
              <>
                <div className={`history-container ${historyCollapsed ? "collapsed" : ""}`}>
                  <ul className="agent-list">
                    {agents.map(agent => (
                      <li
                        key={agent}
                        className={`agent-item ${selectedAgent === agent ? "active" : ""}`}
                        onClick={() => setSelectedAgent(agent)}
                      >
                        {agent}
                      </li>
                    ))}
                  </ul>
                  <div className="agent-divider" />
                  <div className="chat-history-wrapper">
                    <ChatHistory
                      history={history}
                      onSelectChat={handleSelectChat}
                      onNewChat={createNewChat}
                      onDeleteChat={handleDeleteChat}
                      activeChat={activeChat}
                    />
                  </div>
                </div>

                <div
                  className="chat-section"
                  style={{ marginLeft: historyCollapsed ? 0 : 250 }}
                >
                  <div className="chat-container">
                    <ChatDisplay messages={messages} activeChat={activeChat} />
                    <div className="chat-input-container">
                      <div className="input-wrapper">
                        <ChatInput onSendMessage={handleSendMessage} />
                      </div>
                    </div>
                  </div>
                </div>
              </>
            }
          />
          <Route
            path="/login"
            element={
              <div className="centered-page">
                <LoginPage onLogin={handleLogin} />
              </div>
            }
          />
          <Route
            path="/signup"
            element={
              <div className="centered-page">
                <SignupPage onSignup={handleLogin} />
              </div>
            }
          />
          <Route
            path="/forgot-password"
            element={
              <div className="centered-page">
                <ForgotPasswordPage />
              </div>
            }
          />
        </Routes>
      </div>
    </Router>
  );
};

export default App;
