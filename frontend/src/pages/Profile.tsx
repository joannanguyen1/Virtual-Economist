import React from "react";
import Navbar from "../components/Navbar";
import { getStoredUser } from "../lib/auth";
import "../styles/profile.css";

const Profile: React.FC = () => {
  const user = getStoredUser();

  const housingPreferences = [
    "Philadelphia, PA",
    "New York, NY",
    "Boston, MA",
  ];

  const trackedStocks = ["AAPL", "MSFT", "NVDA", "SPY"];

  return (
    <>
      <Navbar />
      <main className="profile-page">
        <section className="profile-hero">
          <p className="profile-eyebrow">Personalized workspace</p>
          <h1>Your Profile</h1>
          <p>
            Manage your account details and the preferences that shape your
            housing and market experience inside Virtual Economist.
          </p>
        </section>

        <section className="profile-grid">
          <article className="profile-card">
            <p className="profile-card-label">Account</p>
            <h2>{user ? user.username : "Guest User"}</h2>
            <div className="profile-details">
              <div className="profile-detail-row">
                <span>User ID</span>
                <span>{user ? user.id : "--"}</span>
              </div>
              <div className="profile-detail-row">
                <span>Username</span>
                <span>{user ? user.username : "Not signed in"}</span>
              </div>
              <div className="profile-detail-row">
                <span>Email</span>
                <span>{user ? user.email : "No email available"}</span>
              </div>
              <div className="profile-detail-row">
                <span>Status</span>
                <span>{user ? "Authenticated" : "Guest"}</span>
              </div>
            </div>
          </article>

          <article className="profile-card">
            <p className="profile-card-label">Housing preferences</p>
            <h2>Preferred locations</h2>
            <p className="profile-card-copy">
              These locations can be used to personalize housing dashboards,
              affordability views, and city-level analysis.
            </p>
            <div className="profile-pill-group">
              {housingPreferences.map((location) => (
                <span key={location} className="profile-pill">
                  {location}
                </span>
              ))}
            </div>
          </article>

          <article className="profile-card">
            <p className="profile-card-label">Market preferences</p>
            <h2>Tracked stocks</h2>
            <p className="profile-card-copy">
              These tickers can shape your dashboard defaults and market-focused
              assistant sessions.
            </p>
            <div className="profile-pill-group">
              {trackedStocks.map((stock) => (
                <span key={stock} className="profile-pill">
                  {stock}
                </span>
              ))}
            </div>
          </article>

          <article className="profile-card">
            <p className="profile-card-label">Coming next</p>
            <h2>Personalization roadmap</h2>
            <ul className="profile-list">
              <li>Editable housing area preferences</li>
              <li>Saved stock watchlists</li>
              <li>Conversation history shortcuts</li>
              <li>Profile-based assistant defaults</li>
            </ul>
          </article>
        </section>
      </main>
    </>
  );
};

export default Profile;