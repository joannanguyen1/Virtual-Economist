DROP TABLE IF EXISTS users;

CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  username TEXT NOT NULL,
  email TEXT UNIQUE NOT NULL,
  hashed_password TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  email_verified BOOLEAN NOT NULL DEFAULT FALSE,
  email_verify_token_hash TEXT,
  email_verify_expires TIMESTAMPTZ
);
