export type UserRole = "admin" | "housing" | "market";

export interface AuthUser {
  id: number;
  username: string;
  email: string;
  role: UserRole;
}

const TOKEN_KEY = "token";
const USER_KEY = "virtual_economist_user";

const VALID_ROLES: UserRole[] = ["admin", "housing", "market"];

const isUserRole = (value: unknown): value is UserRole =>
  typeof value === "string" && (VALID_ROLES as string[]).includes(value);

const emitAuthChanged = () => {
  window.dispatchEvent(new Event("auth-changed"));
};

export const getAuthToken = (): string | null => {
  return localStorage.getItem(TOKEN_KEY);
};

export const getStoredUser = (): AuthUser | null => {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) {
    return null;
  }

  try {
    const parsed = JSON.parse(raw) as Partial<AuthUser>;
    if (
      typeof parsed?.id !== "number" ||
      typeof parsed?.username !== "string" ||
      typeof parsed?.email !== "string" ||
      !isUserRole(parsed?.role)
    ) {
      return null;
    }
    return parsed as AuthUser;
  } catch {
    localStorage.removeItem(USER_KEY);
    return null;
  }
};

export const setAuthSession = (token: string, user: AuthUser) => {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
  emitAuthChanged();
};

export const clearAuthSession = () => {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  emitAuthChanged();
};

// ---------------------------------------------------------------------------
// Role helpers
// ---------------------------------------------------------------------------

export type AgentMode = "auto" | "housing" | "market";

export const allowedAgentModes = (role: UserRole | null | undefined): AgentMode[] => {
  if (role === "admin") return ["auto", "housing", "market"];
  if (role === "housing") return ["housing"];
  if (role === "market") return ["market"];
  return [];
};

export const canUseAgentMode = (
  role: UserRole | null | undefined,
  mode: AgentMode,
): boolean => allowedAgentModes(role).includes(mode);

export const isAdmin = (role: UserRole | null | undefined): boolean => role === "admin";
