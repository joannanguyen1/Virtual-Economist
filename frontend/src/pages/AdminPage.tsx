import React, { useCallback, useEffect, useState } from "react";
import Navbar from "../components/Navbar";
import { getAgentApiBase } from "../lib/api";
import { clearAuthSession, getAuthToken, getStoredUser, UserRole } from "../lib/auth";
import "../styles/admin.css";

interface AdminUser {
  id: number;
  username: string;
  email: string;
  role: UserRole;
  email_verified: boolean;
  created_at: string;
}

const ROLE_OPTIONS: UserRole[] = ["admin", "housing", "market"];
const API_BASE = getAgentApiBase();

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;

const extractApiErrorMessage = (payload: unknown, fallback: string): string => {
  if (!isRecord(payload)) return fallback;

  const detail = payload.detail;
  if (typeof detail === "string" && detail.trim().length > 0) return detail;

  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as unknown;
    if (typeof first === "string" && first.trim().length > 0) return first;
    if (isRecord(first)) {
      const msg = first.msg;
      if (typeof msg === "string" && msg.trim().length > 0) return msg;
    }
    try {
      return JSON.stringify(detail);
    } catch {
      return fallback;
    }
  }

  const error = payload.error;
  if (typeof error === "string" && error.trim().length > 0) return error;

  return fallback;
};

const AdminPage: React.FC = () => {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [savingId, setSavingId] = useState<number | null>(null);

  const me = getStoredUser();

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const token = getAuthToken();
      const res = await fetch(`${API_BASE}/api/admin/users`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        if (res.status === 401) {
          clearAuthSession();
          throw new Error("Session expired. Log in again.");
        }
        throw new Error(`Failed to load users (status ${res.status}).`);
      }
      const data = (await res.json()) as AdminUser[];
      setUsers(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load users.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchUsers();
  }, [fetchUsers]);

  const handleRoleChange = async (userId: number, role: UserRole) => {
    setSavingId(userId);
    setError(null);
    setSuccess(null);
    try {
      const token = getAuthToken();
      const res = await fetch(`${API_BASE}/api/admin/users/${userId}/role`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ role }),
      });
      const payload: unknown = await res.json().catch(() => ({}));
      if (!res.ok) {
        if (res.status === 401) {
          clearAuthSession();
          throw new Error("Session expired. Log in again.");
        }
        const detail = extractApiErrorMessage(
          payload,
          `Failed to update role (status ${res.status}).`,
        );
        throw new Error(detail);
      }
      const updated = payload as AdminUser;
      setUsers((prev) => prev.map((u) => (u.id === userId ? updated : u)));
      setSuccess(`Updated ${updated.username} → ${updated.role}.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update role.");
    } finally {
      setSavingId(null);
    }
  };

  return (
    <>
      <Navbar />
      <main className="admin-page">
        <div className="admin-container">
          <header className="admin-header">
            <h1>User administration</h1>
            <p>Assign roles. Changes take effect immediately on the user's next request.</p>
          </header>

          {error ? <div className="admin-banner admin-banner--error">{error}</div> : null}
          {success ? (
            <div className="admin-banner admin-banner--success">{success}</div>
          ) : null}

          {loading ? (
            <div className="admin-loading">Loading users…</div>
          ) : (
            <div className="admin-table-wrap">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Username</th>
                    <th>Email</th>
                    <th>Verified</th>
                    <th>Role</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => {
                    const isSelf = me?.id === u.id;
                    return (
                      <tr key={u.id}>
                        <td>{u.id}</td>
                        <td>
                          {u.username}
                          {isSelf ? <span className="admin-self-pill">You</span> : null}
                        </td>
                        <td>{u.email}</td>
                        <td>{u.email_verified ? "Yes" : "No"}</td>
                        <td>
                          <select
                            className="admin-role-select"
                            value={u.role}
                            disabled={savingId === u.id}
                            onChange={(e) =>
                              void handleRoleChange(u.id, e.target.value as UserRole)
                            }
                          >
                            {ROLE_OPTIONS.map((r) => (
                              <option key={r} value={r}>
                                {r}
                              </option>
                            ))}
                          </select>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>
    </>
  );
};

export default AdminPage;
