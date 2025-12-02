jest.mock("jsonwebtoken");
jest.mock("bcrypt");
jest.mock("../api/utils/db", () => ({
  query: jest.fn(),
}));

const jwt = require("jsonwebtoken");
const bcrypt = require("bcrypt");
const pool = require("../api/utils/db");
const authService = require("../api/services/authService");

describe("authService", () => {
  afterEach(() => {
    jest.clearAllMocks();
  });
  // Login Tests
  describe("login", () => {
    // it("should return a token on successful login", async () => {
    //   const mockUser = { id: 1, user_name: "user1", hashed_pass: "hashedPass" };
    //   pool.query.mockResolvedValue({ rows: [mockUser] });
    //   bcrypt.compare.mockResolvedValue(true);
    //   jwt.sign.mockReturnValue("fakeToken");

    //   // Call the login function
    //   const result = await authService.login("user1", "password");
    //   expect(pool.query).toHaveBeenCalledWith(
    //     "SELECT * FROM users WHERE user_name = $1",
    //     ["user1"]
    //   );
    //   expect(bcrypt.compare).toHaveBeenCalledWith("password", "hashedPass");
    //   expect(jwt.sign).toHaveBeenCalledWith(
    //     { userId: 1, username: "user1" },
    //     expect.any(String), // secretKey
    //     { expiresIn: "7d" }
    //   );
    //   expect(result).toBe("fakeToken");
    // });

    it("should throw an error for invalid username", async () => {
      // Mock the database query to return no user
      pool.query.mockResolvedValue({ rows: [] });

      await expect(
        authService.login("invalidUser", "password")
      ).rejects.toThrow("Invalid username or password");
    });

    it("should throw an error for invalid password", async () => {
      const mockUser = { id: 1, user_name: "user1", hashed_pass: "hashedPass" };
      pool.query.mockResolvedValue({ rows: [mockUser] });
      bcrypt.compare.mockResolvedValue(false);

      await expect(authService.login("user1", "wrongPassword")).rejects.toThrow(
        "Invalid username or password"
      );
    });
  });

  // Signup Tests
  describe("signup", () => {
    // it("should return a token on successful signup", async () => {
    //   bcrypt.hash.mockResolvedValue("hashedPass");
    //   pool.query.mockResolvedValue({ rows: [{ id: 1 }] });
    //   jwt.sign.mockReturnValue("fakeToken");

    //   const result = await authService.signup(
    //     "user1",
    //     "password",
    //     "user1@example.com"
    //   );
    //   expect(result).toBe("fakeToken");
    // });

    it("should throw error for duplicate username", async () => {
      pool.query.mockResolvedValue({ rows: [{ id: 1 }] });

      await expect(
        authService.signup("user1", "password", "user1@example.com")
      ).rejects.toThrow(
        "This username is already taken. Please choose another."
      );
    });

    it("should throw error for duplicate email", async () => {
      pool.query
        .mockResolvedValueOnce({ rows: [] }) // No duplicate username
        .mockResolvedValueOnce({ rows: [{ id: 1 }] }); // Duplicate email

      await expect(
        authService.signup("user2", "password", "user1@example.com")
      ).rejects.toThrow(
        "An account with this email already exists. Try logging in instead."
      );
    });
  });

  // Logout Test
  describe("logout", () => {
    it("should always return true", () => {
      expect(authService.logout("fakeToken")).toBe(true);
    });
  });

  // Verify Token Tests
  describe("verifyToken", () => {
    let req, res, next;

    beforeEach(() => {
      req = { headers: { authorization: "Bearer fakeToken" } };
      res = { status: jest.fn().mockReturnThis(), json: jest.fn() };
      next = jest.fn();
    });

    // it("should call next if token is valid", () => {
    //   jwt.verify.mockImplementation((token, secret, callback) =>
    //     callback(null, { userId: 1, username: "user1" })
    //   );

    //   authService.verifyToken(req, res, next);
    //   expect(next).toHaveBeenCalled();
    // });

    it("should return 401 if token is missing", () => {
      req.headers.authorization = null;
      authService.verifyToken(req, res, next);
      expect(res.status).toHaveBeenCalledWith(401);
      expect(res.json).toHaveBeenCalledWith({
        message: "Unauthorized: Token missing",
      });
    });

    it("should return 403 if token is invalid", () => {
      jwt.verify.mockImplementation((token, secret, callback) =>
        callback(new Error("Invalid token"))
      );

      authService.verifyToken(req, res, next);
      expect(res.status).toHaveBeenCalledWith(403);
      expect(res.json).toHaveBeenCalledWith({
        message: "Forbidden: Invalid token",
      });
    });
  });
});
