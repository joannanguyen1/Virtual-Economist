const jwt = require("jsonwebtoken");
const bcrypt = require("bcrypt");
const pool = require("../utils/db");
require("dotenv").config();

const secretKey = process.env.JWT_SECRET_KEY;

if (!secretKey) {
  throw new Error(
    "JWT_SECRET_KEY is not set. Please define it in your .env file."
  );
}

const saltRounds = 10;

const login = async (username, password) => {
  try {
    const result = await pool.query(
      "SELECT * FROM users WHERE user_name = $1",
      [username]
    );

    if (result.rows.length === 0) {
      throw new Error("Invalid username or password");
    }

    const user = result.rows[0];
    const isPasswordMatch = await bcrypt.compare(password, user.hashed_pass);

    if (!isPasswordMatch) {
      throw new Error("Invalid username or password");
    }

    const token = jwt.sign({ userId: user.id, username }, secretKey, {
      expiresIn: "7d",
    });
    return token;
  } catch (error) {
    throw new Error(error.message);
  }
};

const signup = async (username, password, email) => {
  try {
    const existingUser = await pool.query(
      "SELECT * FROM users WHERE user_name = $1",
      [username]
    );

    if (existingUser.rows.length > 0) {
      throw new Error("This username is already taken. Please choose another.");
    }

    const existingEmail = await pool.query(
      "SELECT * FROM users WHERE email = $1",
      [email]
    );
    if (existingEmail.rows.length > 0) {
      throw new Error(
        "An account with this email already exists. Try logging in instead."
      );
    }

    const hashedPassword = await bcrypt.hash(password, saltRounds);

    const newUser = await pool.query(
      "INSERT INTO users (user_name, hashed_pass, email) VALUES ($1, $2, $3) RETURNING id",
      [username, hashedPassword, email]
    );
    const userId = newUser.rows[0].id;

    const token = jwt.sign({ userId: userId, username }, secretKey, {
      expiresIn: "7d",
    });
    return token;
  } catch (error) {
    throw new Error(error.message);
  }
};

const logout = (token) => {
  return true;
};

const verifyToken = (req, res, next) => {
  const authHeader = req.headers["authorization"];
  const token = authHeader && authHeader.split(" ")[1];

  if (!token) {
    return res.status(401).json({ message: "Unauthorized: Token missing" });
  }

  jwt.verify(token, secretKey, (err, user) => {
    if (err) {
      return res.status(403).json({ message: "Forbidden: Invalid token" });
    }
    req.user = user;
    next();
  });
};

module.exports = { login, signup, logout, verifyToken };
