const pool = require("../utils/db");

const guestChats = new Map();

const createChat = async (userId) => {
  if (userId === 'guest') {
    const chatId = Date.now();
    const chat = {
      chat_id: chatId,
      user_id: 'guest',
      started_at: new Date(),
      last_updated: new Date()
    };
    guestChats.set(chatId, {
      ...chat,
      messages: []
    });
    return chat;
  }

  const result = await pool.query(
    "INSERT INTO chats (user_id) VALUES ($1) RETURNING *",
    [userId]
  );
  return result.rows[0];
};

const addMessage = async (chatId, userId, messageText, isClient) => {
  try {
    if (userId === 'guest') {
      const chat = guestChats.get(chatId);
      if (!chat) {
        throw new Error("Chat not found");
      }
      const message = {
        message_text: messageText,
        timestamp: new Date(),
        is_client: isClient
      };
      chat.messages.push(message);
      chat.last_updated = new Date();
      return message;
    }

    const result = await pool.query(
      "INSERT INTO messages (chat_id, user_id, message_text, is_client) VALUES ($1, $2, $3, $4) RETURNING *",
      [chatId, userId, messageText, isClient]
    );
    return result.rows[0];
  } catch (error) {
    console.error("Error adding message:", error);
    throw new Error("Failed to add message");
  }
};

const getChatHistory = async (chatId, userId) => {
  if (userId === 'guest') {
    const chat = guestChats.get(chatId);
    if (!chat) {
      throw new Error("Chat not found");
    }
    return {
      chat_id: chat.chat_id,
      started_at: chat.started_at,
      last_updated: chat.last_updated,
      messages: chat.messages.map(msg => ({
        message: msg.message_text,
        timestamp: msg.timestamp,
        is_client: msg.is_client
      }))
    };
  }

  const chatResult = await pool.query(
    "SELECT chat_id, started_at, last_updated FROM chats WHERE chat_id = $1 AND user_id = $2",
    [chatId, userId]
  );

  if (chatResult.rows.length === 0) {
    throw new Error("Chat not found or access denied.");
  }

  const messagesResult = await pool.query(
    `SELECT message_text, timestamp, is_client FROM messages
     WHERE chat_id = $1 AND user_id = $2
     ORDER BY timestamp ASC`,
    [chatId, userId]
  );

  const chat = chatResult.rows[0];
  return {
    chat_id: chat.chat_id,
    started_at: chat.started_at,
    last_updated: chat.last_updated,
    messages: messagesResult.rows.map((msg) => ({
      message: msg.message_text,
      timestamp: msg.timestamp,
      is_client: msg.is_client
    }))
  };
};

const getAllChatHistory = async (userId) => {
  if (userId === 'guest') {
    return Array.from(guestChats.values()).map(chat => ({
      chat_id: chat.chat_id,
      started_at: chat.started_at,
      last_updated: chat.last_updated,
      messages: chat.messages.map(msg => ({
        message: msg.message_text,
        timestamp: msg.timestamp,
        is_client: msg.is_client
      }))
    }));
  }

  const chatsResult = await pool.query(
    `SELECT c.chat_id, c.started_at, c.last_updated, 
            m.message_text, m.timestamp, m.is_client
     FROM chats c
     LEFT JOIN messages m ON c.chat_id = m.chat_id
     WHERE c.user_id = $1
     ORDER BY c.last_updated DESC, m.timestamp ASC`,
    [userId]
  );

  const chatMap = new Map();
  
  chatsResult.rows.forEach(row => {
    if (!chatMap.has(row.chat_id)) {
      chatMap.set(row.chat_id, {
        chat_id: row.chat_id,
        started_at: row.started_at,
        last_updated: row.last_updated,
        messages: []
      });
    }
    
    if (row.message_text) {
      chatMap.get(row.chat_id).messages.push({
        message: row.message_text,
        timestamp: row.timestamp,
        is_client: row.is_client
      });
    }
  });

  return Array.from(chatMap.values());
};

const deleteChat = async (chatId, userId) => {
  if (userId === 'guest') {
    guestChats.delete(chatId);
    return;
  }

  await pool.query(
    "DELETE FROM chats WHERE chat_id = $1 AND user_id = $2",
    [chatId, userId]
  );
};

module.exports = {
  createChat,
  addMessage,
  getChatHistory,
  getAllChatHistory,
  deleteChat,
};
