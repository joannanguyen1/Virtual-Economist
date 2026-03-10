import React, { useEffect, useState } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { clearAuthSession, getStoredUser } from "../lib/auth";
import "../styles/navbar.css";

const Navbar: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const isLanding = location.pathname === "/";
  const [user, setUser] = useState(() => getStoredUser());

  useEffect(() => {
    const syncUser = () => {
      setUser(getStoredUser());
    };

    window.addEventListener("storage", syncUser);
    window.addEventListener("auth-changed", syncUser);

    return () => {
      window.removeEventListener("storage", syncUser);
      window.removeEventListener("auth-changed", syncUser);
    };
  }, []);

  const handleLogout = () => {
    clearAuthSession();
    navigate("/");
  };

  return (
    <nav className="navbar">
      <Link to="/" className="navbar-brand">
        Virtual Economist
      </Link>
      <div className="navbar-links">
        {isLanding ? (
          <>
            <NavLink to="/features" className="navbar-link">
              Features
            </NavLink>
            <NavLink to="/about" className="navbar-link">
              About
            </NavLink>
            <NavLink to="/assistant" className="navbar-link navbar-link-primary">
              Assistant
            </NavLink>
            {user ? (
              <>
                <span className="navbar-user-pill">{user.username}</span>
                <button
                  type="button"
                  className="navbar-link navbar-logout-button"
                  onClick={handleLogout}
                >
                  Logout
                </button>
              </>
            ) : (
              <NavLink to="/login" className="navbar-link">
                Login
              </NavLink>
            )}
          </>
        ) : (
          <>
            <NavLink
              to="/dashboard"
              className={({ isActive }) => `navbar-link ${isActive ? "active" : ""}`.trim()}
            >
              Overview
            </NavLink>
            <NavLink
              to="/assistant"
              className={({ isActive }) =>
                `navbar-link navbar-link-primary ${isActive ? "active" : ""}`.trim()
              }
            >
              Assistant
            </NavLink>
            <NavLink to="/features" className="navbar-link">
              Features
            </NavLink>
            <NavLink to="/about" className="navbar-link">
              About
            </NavLink>
            {user ? (
              <>
                <span className="navbar-user-pill">{user.username}</span>
                <button
                  type="button"
                  className="navbar-link navbar-logout-button"
                  onClick={handleLogout}
                >
                  Logout
                </button>
              </>
            ) : (
              <NavLink to="/login" className="navbar-link">
                Login
              </NavLink>
            )}
          </>
        )}
      </div>
    </nav>
  );
};

export default Navbar;
