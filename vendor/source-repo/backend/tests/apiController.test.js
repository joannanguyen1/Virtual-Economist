const { handleQuestion } = require("../api/controllers/apiController");
const chatHistoryService = require("../api/services/chatHistoryService");
const pythonService = require("../api/services/pythonService");

jest.mock("../api/services/chatHistoryService");
jest.mock("../api/services/pythonService");

const mockRequest = (body = {}, user = {}) => ({
  body,
  user,
});

const mockResponse = () => {
  const res = {};
  res.status = jest.fn().mockReturnValue(res);
  res.json = jest.fn().mockReturnValue(res);
  return res;
};

describe("API Controller - handleQuestion", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should return a valid answer when the question is provided", async () => {
    const req = mockRequest(
      { question: "What is the GDP?", agentSelection: {}, chatId: "123" },
      { userId: "user1" }
    );
    const res = mockResponse();

    pythonService.invokePython.mockResolvedValue("Sample Answer");
    chatHistoryService.addMessage.mockResolvedValue();

    await handleQuestion(req, res);

    expect(pythonService.invokePython).toHaveBeenCalledWith(
      "What is the GDP?",
      {}
    );
    expect(chatHistoryService.addMessage).toHaveBeenCalledTimes(2); // once for question, once for answer
    expect(chatHistoryService.addMessage).toHaveBeenNthCalledWith(
      1,
      "123",
      "user1",
      "What is the GDP?",
      true
    );
    expect(chatHistoryService.addMessage).toHaveBeenNthCalledWith(
      2,
      "123",
      "user1",
      "Sample Answer",
      false
    );
    expect(res.status).toHaveBeenCalledWith(200);
    expect(res.json).toHaveBeenCalledWith({ answer: "Sample Answer" });
  });

  it("should return 400 if the question is missing", async () => {
    const req = mockRequest({}, { userId: "user1" });
    const res = mockResponse();

    await handleQuestion(req, res);

    expect(res.status).toHaveBeenCalledWith(400);
    expect(res.json).toHaveBeenCalledWith({ error: "Question is required" });
  });

  it("should return 500 if adding message to chat history fails", async () => {
    const req = mockRequest(
      { question: "What is the GDP?", agentSelection: {}, chatId: "123" },
      { userId: "user1" }
    );
    const res = mockResponse();

    chatHistoryService.addMessage.mockRejectedValue(
      new Error("Database error")
    );

    await handleQuestion(req, res);

    expect(res.status).toHaveBeenCalledWith(500);
    expect(res.json).toHaveBeenCalledWith({ error: "Internal server error" });
  });

  it("should return 500 if Python service invocation fails", async () => {
    const req = mockRequest(
      { question: "What is the GDP?", agentSelection: {}, chatId: "123" },
      { userId: "user1" }
    );
    const res = mockResponse();

    pythonService.invokePython.mockRejectedValue(
      new Error("Python script error")
    );

    await handleQuestion(req, res);

    expect(res.status).toHaveBeenCalledWith(500);
    expect(res.json).toHaveBeenCalledWith({ error: "Internal server error" });
  });

  it("should handle unexpected errors gracefully", async () => {
    const req = mockRequest(
      { question: "What is the GDP?", agentSelection: {}, chatId: "123" },
      { userId: "user1" }
    );
    const res = mockResponse();

    pythonService.invokePython.mockImplementation(() => {
      throw new Error("Unexpected error");
    });

    await handleQuestion(req, res);

    expect(res.status).toHaveBeenCalledWith(500);
    expect(res.json).toHaveBeenCalledWith({ error: "Internal server error" });
  });
});
