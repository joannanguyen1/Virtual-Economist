import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import Navbar from "../components/Navbar";
import { clearAuthSession, getStoredUser } from "../lib/auth";
import "../styles/profile.css";

const Profile: React.FC = () => {
  const navigate = useNavigate();
  const user = getStoredUser();
  const [copied, setCopied] = useState(false);

  if (!user) {
    navigate("/login");
    return null;
  }

  const handleLogout = () => {
    clearAuthSession();
    navigate("/");
  };

  const handleCopyEmail = () => {
    navigator.clipboard.writeText(user.email);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  const initials = user.username.slice(0, 2).toUpperCase();

  return (
    <>
      <Navbar />
      <div className="profile-page">
        <div className="profile-orb profile-orb--teal" aria-hidden="true" />
        <div className="profile-orb profile-orb--warm" aria-hidden="true" />

        <div className="profile-layout">

          {/* Avatar + name card */}
          <div className="profile-hero">
            <div className="profile-avatar">{initials}</div>
            <div className="profile-hero-text">
              <div className="profile-eyebrow">ACCOUNT</div>
              <h1 className="profile-name">{user.username}</h1>
              <p className="profile-email">{user.email}</p>
            </div>
          </div>

          {/* Info cards */}
          <div className="profile-grid">

            <section className="profile-card">
              <div className="profile-card-label">USERNAME</div>
              <div className="profile-card-value">{user.username}</div>
            </section>

            <section className="profile-card">
              <div className="profile-card-label">EMAIL</div>
              <div className="profile-card-value profile-card-copyable" onClick={handleCopyEmail}>
                <span>{user.email}</span>
                <button className="profile-copy-btn" type="button" aria-label="Copy email">
                  {copied ? (
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  ) : (
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <rect x="9" y="9" width="13" height="13" rx="2" />
                      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                    </svg>
                  )}
                </button>
              </div>
            </section>

            <section className="profile-card">
              <div className="profile-card-label">USER ID</div>
              <div className="profile-card-value profile-card-mono">#{user.id}</div>
            </section>

            <section className="profile-card">
              <div className="profile-card-label">PLAN</div>
              <div className="profile-card-value">
                <span className="profile-plan-badge">Free</span>
              </div>
            </section>

          </div>

          {/* Actions */}
          <div className="profile-actions">
            <button className="profile-action-btn profile-action-btn--primary" onClick={() => navigate("/assistant")}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
              Open Assistant
            </button>
            <button className="profile-action-btn profile-action-btn--ghost" onClick={() => navigate("/dashboard")}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="3" width="7" height="9" rx="1" />
                <rect x="14" y="3" width="7" height="5" rx="1" />
                <rect x="14" y="12" width="7" height="9" rx="1" />
                <rect x="3" y="16" width="7" height="5" rx="1" />
              </svg>
              Dashboard
            </button>
            <button className="profile-action-btn profile-action-btn--danger" onClick={handleLogout}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                <polyline points="16 17 21 12 16 7" />
                <line x1="21" y1="12" x2="9" y2="12" />
              </svg>
              Log out
            </button>
          </div>

        </div>
      </div>
    </>
  );
};

export default Profile;
