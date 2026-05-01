import React, { useEffect, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { allowedAgentModes, AgentMode, getAuthToken, getStoredUser, UserRole } from "../lib/auth";

interface ProtectedRouteProps {
  children: React.ReactNode;
  requireRole?: UserRole | UserRole[];
  requireAgentMode?: AgentMode;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requireRole,
  requireAgentMode,
}) => {
  const location = useLocation();
  const [auth, setAuth] = useState(() => ({
    token: getAuthToken(),
    user: getStoredUser(),
  }));

  useEffect(() => {
    const sync = () => setAuth({ token: getAuthToken(), user: getStoredUser() });
    window.addEventListener("storage", sync);
    window.addEventListener("auth-changed", sync);
    return () => {
      window.removeEventListener("storage", sync);
      window.removeEventListener("auth-changed", sync);
    };
  }, []);

  if (!auth.token || !auth.user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  if (requireRole) {
    const allowed = Array.isArray(requireRole) ? requireRole : [requireRole];
    if (!allowed.includes(auth.user.role)) {
      return <Navigate to="/assistant" replace />;
    }
  }

  if (requireAgentMode) {
    const modes = allowedAgentModes(auth.user.role);
    if (!modes.includes(requireAgentMode)) {
      const fallback = modes[0];
      return <Navigate to={fallback ? `/assistant?mode=${fallback}` : "/assistant"} replace />;
    }
  }

  return <>{children}</>;
};

export default ProtectedRoute;
