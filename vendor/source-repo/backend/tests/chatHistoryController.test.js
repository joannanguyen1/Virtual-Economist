const {
  createChat,
  addMessage,
  getChatHistory,
  getAllChatHistory,
  deleteChat,
} = require("../api/controllers/chatHistoryController");
const chatService = require("../api/services/chatHistoryService");

// Mocking the chatService functions
jest.mock("../api/services/chatHistoryService");

// Mocking request and response objects
const mockRequest = (body = {}, params = {}) => ({
  body,
  params,
  user: { userId: "123" },
});
const mockResponse = () => {
  const res = {};
  res.status = jest.fn().mockReturnValue(res);
  res.json = jest.fn().mockReturnValue(res);
  res.send = jest.fn().mockReturnValue(res);
  return res;
};

describe("Chat Controller", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe("createChat", () => {
    it("should create a chat successfully", async () => {
      const req = mockRequest();
      const res = mockResponse();
      chatService.createChat.mockResolvedValue({ chat_id: "1" });

      await createChat(req, res);

      expect(res.status).toHaveBeenCalledWith(201);
      expect(res.json).toHaveBeenCalledWith({ chat_id: "1" });
    });

    it("should handle errors when creating a chat", async () => {
      const req = mockRequest();
      const res = mockResponse();
      chatService.createChat.mockRejectedValue(
        new Error("Failed to create chat")
      );

      await createChat(req, res);

      expect(res.status).toHaveBeenCalledWith(500);
      expect(res.json).toHaveBeenCalledWith({ error: "Failed to create chat" });
    });
  });

  describe("addMessage", () => {
    it("should add a message successfully", async () => {
      const req = mockRequest(
        { message: "Hello", isClient: true },
        { chatId: "1" }
      );
      const res = mockResponse();
      chatService.addMessage.mockResolvedValue({
        message: "Hello",
        is_client: true,
      });

      await addMessage(req, res);

      expect(res.status).toHaveBeenCalledWith(201);
      expect(res.json).toHaveBeenCalledWith({
        message: "Hello",
        is_client: true,
      });
    });

    it("should return 400 if message or isClient is missing", async () => {
      const req = mockRequest({}, { chatId: "1" });
      const res = mockResponse();

      await addMessage(req, res);

      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith({
        error: "Message and isClient flag are required.",
      });
    });

    it("should handle errors when adding message", async () => {
      const req = {
        params: { chatId: "123" },
        body: { message: "Hello", isClient: true },
        user: { userId: "user1" },
      };
      const res = {
        status: jest.fn().mockReturnThis(),
        json: jest.fn(),
      };

      chatService.addMessage = jest
        .fn()
        .mockRejectedValue(new Error("Failed to add message"));

      await addMessage(req, res);

      expect(chatService.addMessage).toHaveBeenCalledWith(
        "123",
        "user1",
        "Hello",
        true
      );
      expect(res.status).toHaveBeenCalledWith(500);
      expect(res.json).toHaveBeenCalledWith({
        error: "Failed to add message",
      });
    });
  });

  describe("getChatHistory", () => {
    it("should retrieve chat history successfully", async () => {
      const req = mockRequest({}, { chatId: "1" });
      const res = mockResponse();
      chatService.getChatHistory.mockResolvedValue({
        chat_id: "1",
        messages: [],
      });

      await getChatHistory(req, res);

      expect(res.status).toHaveBeenCalledWith(200);
      expect(res.json).toHaveBeenCalledWith({ chat_id: "1", messages: [] });
    });

    it("should handle errors when retrieving chat history", async () => {
      const req = mockRequest({}, { chatId: "1" });
      const res = mockResponse();
      chatService.getChatHistory.mockRejectedValue(
        new Error("Failed to retrieve chat history")
      );

      await getChatHistory(req, res);

      expect(res.status).toHaveBeenCalledWith(500);
      expect(res.json).toHaveBeenCalledWith({
        error: "Failed to retrieve chat history",
      });
    });
  });

  describe("getAllChatHistory", () => {
    it("should retrieve all chat history successfully", async () => {
      const req = mockRequest();
      const res = mockResponse();
      chatService.getAllChatHistory.mockResolvedValue([
        { chat_id: "1", messages: [] },
      ]);

      await getAllChatHistory(req, res);

      expect(res.status).toHaveBeenCalledWith(200);
      expect(res.json).toHaveBeenCalledWith([{ chat_id: "1", messages: [] }]);
    });

    it("should handle errors when retrieving all chat history", async () => {
      const req = mockRequest();
      const res = mockResponse();
      chatService.getAllChatHistory.mockRejectedValue(
        new Error("Failed to retrieve all chat history")
      );

      await getAllChatHistory(req, res);

      expect(res.status).toHaveBeenCalledWith(500);
      expect(res.json).toHaveBeenCalledWith({
        error: "Failed to retrieve all chat history",
      });
    });
  });

  describe("deleteChat", () => {
    it("should delete a chat successfully", async () => {
      const req = mockRequest({}, { chatId: "1" });
      const res = mockResponse();
      chatService.deleteChat.mockResolvedValue();

      await deleteChat(req, res);

      expect(res.status).toHaveBeenCalledWith(204);
      expect(res.send).toHaveBeenCalled();
    });

    it("should handle errors when deleting a chat", async () => {
      const req = mockRequest({}, { chatId: "1" });
      const res = mockResponse();
      chatService.deleteChat.mockRejectedValue(
        new Error("Failed to delete chat")
      );

      await deleteChat(req, res);

      expect(res.status).toHaveBeenCalledWith(500);
      expect(res.json).toHaveBeenCalledWith({ error: "Failed to delete chat" });
    });
  });
});
