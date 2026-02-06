const pythonService = require("../services/pythonService");
const chatHistoryService = require("../services/chatHistoryService");

const handleQuestion = async (req, res) => {
  try {
    const { question, agentSelection, chatId } = req.body;
    if (!question) {
      return res.status(400).json({ error: "Question is required" });
    }
    if (req.user.userId !== 'guest') {
      await chatHistoryService.addMessage(chatId, req.user.userId, question, true);
    }
    const answer = await pythonService.invokePython(question, agentSelection);
    if (req.user.userId !== 'guest') {
      await chatHistoryService.addMessage(chatId, req.user.userId, answer, false);
    }
    res.json({ answer });
  } catch (error) {
    console.error("Error in handleQuestion:", error);
    res.status(500).json({ error: "Internal server error" });
  }
};

module.exports = { handleQuestion };
