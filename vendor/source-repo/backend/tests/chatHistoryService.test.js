const chatHistoryService = require("../api/services/chatHistoryService");
const pool = require("../api/utils/db");

// Mock the database pool
jest.mock("../api/utils/db");

describe("Chat History Service", () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  describe("createChat", () => {
    it("should create a chat and return the chat object", async () => {
      const mockChat = { chat_id: 1, user_id: 100 };
      pool.query.mockResolvedValue({ rows: [mockChat] });

      const result = await chatHistoryService.createChat(100);

      expect(result).toEqual(mockChat);
      expect(pool.query).toHaveBeenCalledWith(
        "INSERT INTO chats (user_id) VALUES ($1) RETURNING *",
        [100]
      );
    });

    it("should throw an error if chat creation fails", async () => {
      pool.query.mockRejectedValue(new Error("Database error"));

      await expect(chatHistoryService.createChat(100)).rejects.toThrow(
        "Database error"
      );
    });
  });

  describe("addMessage", () => {
    it("should add a message and return the message object", async () => {
      const mockMessage = {
        chat_id: 1,
        user_id: 100,
        message_text: "Hello",
        is_client: true,
      };
      pool.query.mockResolvedValue({ rows: [mockMessage] });

      const result = await chatHistoryService.addMessage(1, 100, "Hello", true);

      expect(result).toEqual(mockMessage);
      expect(pool.query).toHaveBeenCalledWith(
        "INSERT INTO messages (chat_id, user_id, message_text, is_client) VALUES ($1, $2, $3, $4) RETURNING *",
        [1, 100, "Hello", true]
      );
    });

    it("should throw an error if adding message fails", async () => {
      pool.query.mockRejectedValue(new Error("Failed to add message"));

      await expect(
        chatHistoryService.addMessage(1, 100, "Hello", true)
      ).rejects.toThrow("Failed to add message");
    });
  });

  describe("getChatHistory", () => {
    it("should return chat history for a given chat ID and user ID", async () => {
      const mockChat = {
        chat_id: 1,
        started_at: "2023-01-01",
        last_updated: "2023-01-02",
      };
      const mockMessages = [
        { message_text: "Hello", timestamp: "2023-01-01", is_client: true },
        { message_text: "Hi", timestamp: "2023-01-02", is_client: false },
      ];

      pool.query
        .mockResolvedValueOnce({ rows: [mockChat] }) // Chat exists
        .mockResolvedValueOnce({ rows: mockMessages }); // Messages

      const result = await chatHistoryService.getChatHistory(1, 100);

      expect(result).toEqual({
        chat_id: 1,
        started_at: "2023-01-01",
        last_updated: "2023-01-02",
        messages: [
          { message: "Hello", timestamp: "2023-01-01", is_client: true },
          { message: "Hi", timestamp: "2023-01-02", is_client: false },
        ],
      });
    });

    it("should throw an error if chat not found", async () => {
      pool.query.mockResolvedValueOnce({ rows: [] });

      await expect(chatHistoryService.getChatHistory(1, 100)).rejects.toThrow(
        "Chat not found or access denied."
      );
    });
  });

  describe("getAllChatHistory", () => {
    it("should return all chat histories for a given user", async () => {
      const mockChats = [
        { chat_id: 1, started_at: "2023-01-01", last_updated: "2023-01-02" },
        { chat_id: 2, started_at: "2023-01-03", last_updated: "2023-01-04" },
      ];
      const mockMessages = [
        { message_text: "Hello", timestamp: "2023-01-01", is_client: true },
        { message_text: "Hi", timestamp: "2023-01-02", is_client: false },
      ];

      pool.query
        .mockResolvedValueOnce({ rows: mockChats }) // Chats list
        .mockResolvedValue({ rows: mockMessages }); // Messages for each chat

      const result = await chatHistoryService.getAllChatHistory(100);

      expect(result).toEqual([
        {
          chat_id: 1,
          started_at: "2023-01-01",
          last_updated: "2023-01-02",
          messages: [
            { message: "Hello", timestamp: "2023-01-01", is_client: true },
            { message: "Hi", timestamp: "2023-01-02", is_client: false },
          ],
        },
        {
          chat_id: 2,
          started_at: "2023-01-03",
          last_updated: "2023-01-04",
          messages: [
            { message: "Hello", timestamp: "2023-01-01", is_client: true },
            { message: "Hi", timestamp: "2023-01-02", is_client: false },
          ],
        },
      ]);
    });
  });

  describe("deleteChat", () => {
    it("should delete a chat by ID and user ID", async () => {
      pool.query.mockResolvedValue({});

      await chatHistoryService.deleteChat(1, 100);

      expect(pool.query).toHaveBeenCalledWith(
        "DELETE FROM chats WHERE chat_id = $1 AND user_id = $2",
        [1, 100]
      );
    });

    it("should handle errors when deleting a chat", async () => {
      pool.query.mockRejectedValue(new Error("Database error"));

      await expect(chatHistoryService.deleteChat(1, 100)).rejects.toThrow(
        "Database error"
      );
    });
  });
});
