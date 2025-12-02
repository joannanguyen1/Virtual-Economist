const chatService = require("../services/chatHistoryService");

const createChat = async (req, res) => {
  try {
    const userId = req.user.userId;
    const chat = await chatService.createChat(userId);
    res.status(201).json(chat);
  } catch (error) {
    res.status(500).json({ error: "Failed to create chat" });
  }
};

const addMessage = async (req, res) => {
  try {
    const { chatId } = req.params;
    const { message, isClient } = req.body;

    if (!message || typeof isClient !== "boolean") {
      return res
        .status(400)
        .json({ error: "Message and isClient flag are required." });
    }

    const userId = req.user.userId;
    const newMessage = await chatService.addMessage(
      chatId,
      userId,
      message,
      isClient
    );
    res.status(201).json(newMessage);
  } catch (error) {
    console.error("Error adding message:", error);
    res.status(500).json({ error: "Failed to add message" });
  }
};

const getChatHistory = async (req, res) => {
  try {
    const { chatId } = req.params;
    const userId = req.user.userId;

    const chat = await chatService.getChatHistory(chatId, userId);
    res.status(200).json(chat);
  } catch (error) {
    res.status(500).json({ error: "Failed to retrieve chat history" });
  }
};

const getAllChatHistory = async (req, res) => {
  try {
    const userId = req.user.userId;
    const allChats = await chatService.getAllChatHistory(userId);
    res.status(200).json(allChats);
  } catch (error) {
    res.status(500).json({ error: "Failed to retrieve all chat history" });
  }
};

const deleteChat = async (req, res) => {
  try {
    const { chatId } = req.params;
    const userId = req.user.userId;

    await chatService.deleteChat(chatId, userId);
    res.status(204).send();
  } catch (error) {
    res.status(500).json({ error: "Failed to delete chat" });
  }
};

module.exports = {
  createChat,
  addMessage,
  getChatHistory,
  getAllChatHistory,
  deleteChat,
};
