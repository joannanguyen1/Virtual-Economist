import express from "express";
import bcrypt from "bcrypt";
import jwt from "jsonwebtoken";
import pool from "../database/db.js";

const router = express.Router();

/**
 * REGISTER
 * Frontend calls: POST /api/register
 * body: { name, email, password }
 */
router.post("/register", async (req, res) => {
  const { name, email, password } = req.body;
  console.log(name, email, password)
  if (!name || !email || !password) {
    return res.status(400).json({ error: "Missing fields" });
  }

  try {
    // check if user exists
    const existing = await pool.query(
      "SELECT id FROM users WHERE email=$1",
      [email]
    );

    if (existing.rows.length > 0) {
      return res.status(409).json({ error: "User already exists" });
    }

    const hashedPassword = await bcrypt.hash(password, 10);

    // map name -> username
    await pool.query(
      `INSERT INTO users (username, email, hashed_password)
       VALUES ($1,$2,$3)`,
      [name, email, hashedPassword]
    );

    res.json({ message: "Signup successful" });

  } catch (err) {
    console.error(err);
    res.status(500).json({ error: "Server error" });
  }
});

/**
 * LOGIN
 * Frontend calls: POST /api/login
 * body: { email, password }
 */
router.post("/login", async (req, res) => {
  const { email, password } = req.body;

  try {
    const result = await pool.query(
      "SELECT * FROM users WHERE email=$1",
      [email]
    );

    if (result.rows.length === 0) {
      return res.status(401).json({ error: "Invalid credentials" });
    }

    const user = result.rows[0];

    const valid = await bcrypt.compare(
      password,
      user.hashed_password
    );

    if (!valid) {
      return res.status(401).json({ error: "Invalid credentials" });
    }

    const token = jwt.sign(
      { id: user.id },
      process.env.JWT_SECRET,
      { expiresIn: "1d" }
    );

    res.json({
      token,
      user: {
        id: user.id,
        username: user.username,
        email: user.email
      }
    });

  } catch (err) {
    console.error(err);
    res.status(500).json({ error: "Server error" });
  }
});

export default router;
