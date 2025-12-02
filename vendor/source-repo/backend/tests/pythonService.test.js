const { invokePython } = require("../api/services/pythonService");
const { spawn } = require("child_process");

// Mocking the child_process spawn method
jest.mock("child_process");

describe("Python Service - invokePython", () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it("should return output when Python script executes successfully", async () => {
    const mockProcess = {
      stdout: {
        on: jest.fn((event, callback) => {
          if (event === "data") callback("Success response from Python");
        }),
      },
      stderr: {
        on: jest.fn(),
      },
      on: jest.fn((event, callback) => {
        if (event === "close") callback(0);
      }),
    };

    spawn.mockReturnValue(mockProcess);

    const result = await invokePython("test", {
      agent: "test_agent",
    });

    expect(result).toBe("Success response from Python");
    expect(spawn).toHaveBeenCalledWith(
      expect.any(String),
      expect.arrayContaining([
        expect.stringContaining("main.py"),
        "test",
        JSON.stringify({ agent: "test_agent" }),
      ])
    );
  });

  it("should throw an error when Python script fails", async () => {
    const mockProcess = {
      stdout: {
        on: jest.fn(),
      },
      stderr: {
        on: jest.fn((event, callback) => {
          if (event === "data") callback("Error response from Python");
        }),
      },
      on: jest.fn((event, callback) => {
        if (event === "close") callback(1);
      }),
    };

    spawn.mockReturnValue(mockProcess);

    await expect(
      invokePython("Invalid question", { agent: "unknown" })
    ).rejects.toBe("Error response from Python");

    expect(spawn).toHaveBeenCalledWith(
      expect.any(String),
      expect.arrayContaining([
        expect.stringContaining("main.py"),
        "Invalid question",
        JSON.stringify({ agent: "unknown" }),
      ])
    );
  });

  it("should handle empty error output when Python script fails", async () => {
    const mockProcess = {
      stdout: {
        on: jest.fn(),
      },
      stderr: {
        on: jest.fn(),
      },
      on: jest.fn((event, callback) => {
        if (event === "close") callback(1);
      }),
    };

    spawn.mockReturnValue(mockProcess);

    await expect(
      invokePython("Some question", { agent: "unknown" })
    ).rejects.toBe("Error occurred in Python script");

    expect(spawn).toHaveBeenCalledWith(
      expect.any(String),
      expect.arrayContaining([
        expect.stringContaining("main.py"),
        "Some question",
        JSON.stringify({ agent: "unknown" }),
      ])
    );
  });
});
