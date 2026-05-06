-- Migration: Add role-based access control to users.
-- Run once on each environment:  psql "$DATABASE_URL" -f 001_add_user_roles.sql

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'housing'
  CHECK (role IN ('admin', 'housing', 'market'));

-- Backfill: existing users were created before RBAC, so promote them all to admin.
-- After running this, manually downgrade demo accounts:
--   UPDATE users SET role = 'housing' WHERE email = 'someone@example.com';
UPDATE users SET role = 'admin' WHERE role = 'housing';
