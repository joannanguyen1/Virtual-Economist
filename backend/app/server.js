import express from "express";
import bcrypt from "bcrypt";
import jwt from "jsonwebtoken";
import pool from "../database/db.js";

import crypto from "crypto";
import nodemailer from "nodemailer";

const router = express.Router();

function normalizeEmail(email) {
  return String(email || "").trim().toLowerCase();
}

function makeVerifyToken() {
  return crypto.randomBytes(32).toString("hex");
}

function hashToken(token) {
  return crypto.createHash("sha256").update(String(token)).digest("hex");
}

const transporter = nodemailer.createTransport({
  host: process.env.SMTP_HOST,              
  port: Number(process.env.SMTP_PORT || 587),
  secure: false,                             
  auth: {
    user: process.env.SMTP_USER,
    pass: process.env.SMTP_PASS,
  },
});

/**
 * REGISTER
 * Frontend calls: POST /api/register
 * body: { name, email, password }
 *
 * Email verification flow (DB token):
 * - Creates the user as unverified (email_verified=false)
 * - Generates a random verification token
 * - Stores token hash + expiry in DB
 * - Sends user a link: APP_URL/verify-email?token=...
 * - Returns: "Check your email"
 */
router.post("/register", async (req, res) => {
  const { name, email, password } = req.body;
  console.log(name, email, password);

  if (!name || !email || !password) {
    return res.status(400).json({ error: "Missing fields" });
  }

  const normalizedEmail = normalizeEmail(email);

  try {
    const existing = await pool.query(
      "SELECT id FROM users WHERE email=$1",
      [normalizedEmail]
    );

    if (existing.rows.length > 0) {
      return res.status(409).json({ error: "User already exists" });
    }

    const hashedPassword = await bcrypt.hash(password, 10);

    const created = await pool.query(
      `INSERT INTO users (username, email, hashed_password)
       VALUES ($1,$2,$3)
       RETURNING id`,
      [name, normalizedEmail, hashedPassword]
    );

    const userId = created.rows[0].id;
    const verifyToken = makeVerifyToken();
    const verifyTokenHash = hashToken(verifyToken);
    const verifyExpires = new Date(Date.now() + 24 * 60 * 60 * 1000);

    await pool.query(
      `UPDATE users
       SET email_verify_token_hash=$1,
           email_verify_expires=$2
       WHERE id=$3`,
      [verifyTokenHash, verifyExpires, userId]
    );

    if (!process.env.APP_URL) {
      return res.status(500).json({ error: "Missing APP_URL env var" });
    }
    if (!process.env.SMTP_HOST || !process.env.SMTP_USER || !process.env.SMTP_PASS) {
      return res.status(500).json({ error: "Missing SMTP env vars (SMTP_HOST/SMTP_USER/SMTP_PASS)" });
    }

    const link = `${process.env.APP_URL}/verify-email?token=${encodeURIComponent(verifyToken)}`;

    try {
      await transporter.verify();

      await transporter.sendMail({
        from: process.env.MAIL_FROM || process.env.SMTP_USER,
        to: normalizedEmail,
        subject: "Verify your email for Virtual Economist",
        text: `Click this link to verify your email (expires in 24 hours):\n\n${link}\n\nIf you did not sign up, ignore this email.`,
      });
    } catch (emailErr) {
      console.error("EMAIL SEND ERROR:", emailErr);

      await pool.query("DELETE FROM users WHERE id=$1", [userId]);

      return res.status(500).json({
        error: "Could not send verification email. Check SMTP settings.",
      });
    }

    return res.json({
      message: "Account created. Check your email for a verification link (also check Promotions/Spam if you don't see it). You must verify before logging in.",
    });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: "Server error" });
  }
});

/**
 * VERIFY EMAIL
 * Frontend calls: GET /api/verify-email?token=...
 *
 * Flow:
 * - hash incoming token
 * - find user with matching token hash
 * - ensure not expired
 * - set email_verified=true and clear token fields
 */
router.get("/verify-email", async (req, res) => {
  const token = req.query.token;

  if (!token) {
    return res.status(400).json({ error: "Missing token" });
  }

  try {
    const tokenHash = hashToken(token);
    const now = new Date();

    const result = await pool.query(
      `SELECT id, email_verify_expires, email_verified
       FROM users
       WHERE email_verify_token_hash=$1`,
      [tokenHash]
    );

    if (result.rows.length === 0) {
      return res.status(400).json({ error: "Invalid verification token" });
    }

    const user = result.rows[0];

    if (user.email_verified) {
      return res.json({ message: "Email already verified. You can log in." });
    }

    if (!user.email_verify_expires || new Date(user.email_verify_expires) < now) {
      return res.status(400).json({ error: "Verification token expired" });
    }

    await pool.query(
      `UPDATE users
       SET email_verified=true,
           email_verify_expires=NULL
       WHERE id=$1`,
      [user.id]
    );

    return res.json({ message: "Email verified! You can now log in." });
  } catch (err) {
    console.error(err);
    return res.status(500).json({ error: "Server error" });
  }
});

/**
 * LOGIN
 * Frontend calls: POST /api/login
 * body: { email, password }
 *
 * Email verification check:
 * - If email_verified is false, block login until they verify
 */
router.post("/login", async (req, res) => {
  const { email, password } = req.body;

  const normalizedEmail = normalizeEmail(email);

  try {
    const result = await pool.query(
      "SELECT * FROM users WHERE email=$1",
      [normalizedEmail]
    );

    if (result.rows.length === 0) {
      return res.status(401).json({ error: "Invalid credentials" });
    }

    const user = result.rows[0];

    if (!user.email_verified) {
      return res.status(403).json({ error: "Please verify your email before logging in." });
    }

    const valid = await bcrypt.compare(password, user.hashed_password);

    if (!valid) {
      return res.status(401).json({ error: "Invalid credentials" });
    }

    if (!process.env.JWT_SECRET) {
      return res.status(500).json({ error: "Missing JWT_SECRET env var" });
    }

    const token = jwt.sign({ id: user.id }, process.env.JWT_SECRET, { expiresIn: "1d" });

    res.json({
      token,
      user: {
        id: user.id,
        username: user.username,
        email: user.email,
      },
    });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: "Server error" });
  }
});

export default router;