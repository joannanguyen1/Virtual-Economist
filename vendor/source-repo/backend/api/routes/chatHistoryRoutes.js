const express = require("express");
const router = express.Router();
const chatController = require("../controllers/chatHistoryController");
const authService = require("../services/authService");

router.post("/create", authService.verifyToken, chatController.createChat);
router.post("/add/:chatId", authService.verifyToken, chatController.addMessage);
router.get("/history/:chatId", authService.verifyToken, chatController.getChatHistory);
router.get("/history", authService.verifyToken, chatController.getAllChatHistory);
router.delete("/history/:chatId", authService.verifyToken, chatController.deleteChat);

module.exports = router;
