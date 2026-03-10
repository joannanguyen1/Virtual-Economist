import express from "express";
import bcrypt from "bcrypt";
import crypto from "crypto";
import jwt from "jsonwebtoken";
import nodemailer from "nodemailer";
import pool from "../database/db.js";

const router = express.Router();
const FRONTEND_BASE_URL = process.env.FRONTEND_BASE_URL || "http://localhost:3000";
const VERIFY_TTL_HOURS = 24;

async function ensureAuthSchema() {
  await pool.query(`
    ALTER TABLE users
    ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT FALSE
  `);
  await pool.query(`
    ALTER TABLE users
    ADD COLUMN IF NOT EXISTS email_verify_token_hash TEXT
  `);
  await pool.query(`
    ALTER TABLE users
    ADD COLUMN IF NOT EXISTS email_verify_expires TIMESTAMPTZ
  `);
  await pool.query(`
    UPDATE users
    SET email_verified = TRUE
    WHERE email_verified = FALSE
      AND email_verify_token_hash IS NULL
      AND email_verify_expires IS NULL
  `);
}

await ensureAuthSchema();

function hashVerificationToken(token) {
  return crypto.createHash("sha256").update(token).digest("hex");
}

function buildVerificationUrl(token) {
  return `${FRONTEND_BASE_URL}/verify-email?token=${token}`;
}

function getVerificationTransport() {
  const host = process.env.SMTP_HOST;
  const port = Number(process.env.SMTP_PORT || 587);
  const user = process.env.SMTP_USER;
  const pass = process.env.SMTP_PASS;

  if (!host || !user || !pass) {
    return null;
  }

  return nodemailer.createTransport({
    host,
    port,
    secure: port === 465,
    auth: { user, pass },
  });
}

async function sendVerificationEmail(email, verificationUrl) {
  const transporter = getVerificationTransport();
  if (!transporter) {
    return false;
  }

  const from = process.env.SMTP_FROM || process.env.SMTP_USER;
  await transporter.sendMail({
    from,
    to: email,
    subject: "Verify your Virtual Economist account",
    text: `Verify your email by opening this link: ${verificationUrl}`,
    html: `
      <p>Verify your Virtual Economist account by clicking the link below.</p>
      <p><a href="${verificationUrl}">${verificationUrl}</a></p>
      <p>This link expires in ${VERIFY_TTL_HOURS} hours.</p>
    `,
  });
  return true;
}

async function issueVerificationForUser(userId, email) {
  const token = crypto.randomBytes(32).toString("hex");
  const tokenHash = hashVerificationToken(token);
  const expiresAt = new Date(Date.now() + VERIFY_TTL_HOURS * 60 * 60 * 1000);

  await pool.query(
    `
      UPDATE users
      SET email_verified = FALSE,
          email_verify_token_hash = $1,
          email_verify_expires = $2
      WHERE id = $3
    `,
    [tokenHash, expiresAt, userId],
  );

  const verificationUrl = buildVerificationUrl(token);
  const emailSent = await sendVerificationEmail(email, verificationUrl).catch((err) => {
    console.error("Verification email failed:", err);
    return false;
  });

  return { verificationUrl, emailSent };
}

/**
 * REGISTER
 * Frontend calls: POST /api/register
 * body: { name, email, password }
 */
router.post("/register", async (req, res) => {
  const { name, email, password } = req.body;
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

    const created = await pool.query(
      `INSERT INTO users (username, email, hashed_password)
       VALUES ($1,$2,$3)
       RETURNING id, email`,
      [name, email, hashedPassword]
    );

    const user = created.rows[0];
    const { verificationUrl, emailSent } = await issueVerificationForUser(
      user.id,
      user.email,
    );

    res.json({
      message: emailSent
        ? "Signup successful. Check your email to verify your account."
        : "Signup successful. Use the verification link below in local development.",
      verificationRequired: true,
      verificationUrl: emailSent ? null : verificationUrl,
    });

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

    if (!user.email_verified) {
      const { verificationUrl, emailSent } = await issueVerificationForUser(
        user.id,
        user.email,
      );
      return res.status(403).json({
        error: emailSent
          ? "Please verify your email before logging in. We sent a new verification email."
          : "Please verify your email before logging in.",
        verificationRequired: true,
        verificationUrl: emailSent ? null : verificationUrl,
      });
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

router.get("/verify-email", async (req, res) => {
  const token = String(req.query.token || "").trim();
  if (!token) {
    return res.status(400).json({ error: "Missing verification token" });
  }

  try {
    const tokenHash = hashVerificationToken(token);
    const result = await pool.query(
      `
        UPDATE users
        SET email_verified = TRUE,
            email_verify_token_hash = NULL,
            email_verify_expires = NULL
        WHERE email_verify_token_hash = $1
          AND email_verify_expires IS NOT NULL
          AND email_verify_expires > NOW()
        RETURNING id, email
      `,
      [tokenHash],
    );

    if (result.rows.length === 0) {
      return res.status(400).json({
        error: "This verification link is invalid or has expired.",
      });
    }

    return res.json({
      message: "Email verified successfully. You can now log in.",
    });
  } catch (err) {
    console.error(err);
    return res.status(500).json({ error: "Server error" });
  }
});

export default router;
