const { login, logout, signup } = require("../api/controllers/authController");
const authService = require("../api/services/authService");

jest.mock("../api/services/authService");

const mockRequest = (body = {}, headers = {}) => ({
  body,
  headers,
});

const mockResponse = () => {
  const res = {};
  res.status = jest.fn().mockReturnValue(res);
  res.json = jest.fn().mockReturnValue(res);
  return res;
};

describe("Auth Controller", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // Login Tests
  describe("Login", () => {
    it("should return a token on successful login", async () => {
      const req = mockRequest({ username: "user1", password: "pass1" });
      const res = mockResponse();
      authService.login.mockResolvedValue("mocked_jwt_token");

      await login(req, res);

      expect(authService.login).toHaveBeenCalledWith("user1", "pass1");
      expect(res.status).not.toHaveBeenCalled();
      expect(res.json).toHaveBeenCalledWith({ token: "mocked_jwt_token" });
    });

    it("should return 400 for invalid credentials", async () => {
      const req = mockRequest({ username: "user1", password: "wrong" });
      const res = mockResponse();
      authService.login.mockRejectedValue(
        new Error("Invalid username or password")
      );

      await login(req, res);

      expect(authService.login).toHaveBeenCalledWith("user1", "wrong");
      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith({
        error: "Invalid username or password",
      });
    });

    it("should return 400 when credentials are missing", async () => {
      const req = mockRequest({});
      const res = mockResponse();

      await login(req, res);

      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith({
        error: "Username and password are required",
      });
    });
  });

  // Logout Tests
  describe("Logout", () => {
    it("should return a success message on logout", () => {
      const req = mockRequest({ token: "mocked_jwt_token" });
      const res = mockResponse();

      authService.logout.mockReturnValue(true);

      logout(req, res);

      expect(authService.logout).toHaveBeenCalledWith("mocked_jwt_token");
      expect(res.json).toHaveBeenCalledWith({
        message: "Logged out successfully",
      });
    });

    it("should return 400 if logout fails", () => {
      const req = mockRequest({ token: "mocked_jwt_token" });
      const res = mockResponse();

      authService.logout.mockImplementation(() => {
        throw new Error("Logout error");
      });

      logout(req, res);

      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith({ error: "Logout error" });
    });
  });

  // Signup Tests
  describe("Signup", () => {
    it("should return a token on successful signup", async () => {
      const req = mockRequest({
        username: "user1",
        password: "pass1",
        email: "user1@example.com",
      });
      const res = mockResponse();
      authService.signup.mockResolvedValue("mocked_jwt_token");

      await signup(req, res);

      expect(authService.signup).toHaveBeenCalledWith(
        "user1",
        "pass1",
        "user1@example.com"
      );
      expect(res.json).toHaveBeenCalledWith({ token: "mocked_jwt_token" });
    });

    it("should return 400 for missing fields", async () => {
      const req = mockRequest({ username: "user1" });
      const res = mockResponse();

      await signup(req, res);

      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith({
        error: "Username, password, and email are required",
      });
    });

    it("should return 400 for duplicate username", async () => {
      const req = mockRequest({
        username: "user1",
        password: "pass1",
        email: "user1@example.com",
      });
      const res = mockResponse();
      authService.signup.mockRejectedValue(
        new Error("This username is already taken. Please choose another.")
      );

      await signup(req, res);

      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith({
        error: "This username is already taken. Please choose another.",
      });
    });

    it("should return 400 for duplicate email", async () => {
      const req = mockRequest({
        username: "user2",
        password: "pass2",
        email: "user1@example.com",
      });
      const res = mockResponse();
      authService.signup.mockRejectedValue(
        new Error(
          "An account with this email already exists. Try logging in instead."
        )
      );

      await signup(req, res);

      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith({
        error:
          "An account with this email already exists. Try logging in instead.",
      });
    });
  });
});
