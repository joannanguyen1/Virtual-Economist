import React from "react";
import Navbar from "../components/Navbar";
import "../styles/features.css";

const features = [
  {
    id: "housing",
    tag: "AGENT",
    accent: "#2fb6a3",
    title: "Housing / City Agent",
    description:
      "Ask about home values, rent affordability, market inventory, and local conditions. City-specific insights powered by structured housing, income, and geographic data.",
    bullets: [
      "Home values & rent trend analysis",
      "Inventory & market speed indicators",
      "Affordability using income estimates",
      "Location-aware context (maps/weather)",
    ],
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 9.5L12 3l9 6.5V21H3V9.5z" />
        <rect x="9" y="14" width="6" height="7" />
      </svg>
    ),
  },
  {
    id: "stock",
    tag: "AGENT",
    accent: "#f4b35f",
    title: "Stock Agent",
    description:
      "Explore market performance, sector movement, and sentiment signals. Complex market data distilled into clear, actionable insights you can actually use.",
    bullets: [
      "Historical ticker trends and movement",
      "Sector performance summaries",
      "News sentiment and market context",
      "Market overview + explainable insights",
    ],
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="22 7 13.5 15.5 8.5 10.5 2 17" />
        <polyline points="16 7 22 7 22 13" />
      </svg>
    ),
  },
  {
    id: "grounded",
    tag: "RELIABILITY",
    accent: "#35d1c5",
    title: "Source-Grounded Answers",
    description:
      "Built to minimize hallucinations by grounding every response in valid data sources. Verifiable, trustworthy outputs — not guesswork.",
    bullets: [
      "Data-backed responses (not guesswork)",
      "Clear, structured explanations",
      "Consistency across sessions",
    ],
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 2L3 7v5c0 5.25 3.75 10.15 9 11.35C17.25 22.15 21 17.25 21 12V7L12 2z" />
        <polyline points="9 12 11 14 15 10" />
      </svg>
    ),
  },
  {
    id: "accounts",
    tag: "PERSONALIZATION",
    accent: "#f4b35f",
    title: "Accounts & Personalization",
    description:
      "Create an account and get a tailored experience that improves over time. Your preferences and chat context make every response more relevant.",
    bullets: [
      "Login + signup flow",
      "User profile & preferences",
      "Personalized dashboard scope",
    ],
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="8" r="4" />
        <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" />
      </svg>
    ),
  },
  {
    id: "history",
    tag: "MEMORY",
    accent: "#2fb6a3",
    title: "Chat History & Search",
    description:
      "Never repeat yourself. Save sessions, search past conversations, and pick up right where you left off with full context intact.",
    bullets: [
      "Session history",
      "Searchable chat archive",
      "Conversation context support",
    ],
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="11" cy="11" r="8" />
        <line x1="21" y1="21" x2="16.65" y2="16.65" />
        <polyline points="11 8 11 11 13 13" />
      </svg>
    ),
  },
  {
    id: "dashboard",
    tag: "VISUALIZATION",
    accent: "#35d1c5",
    title: "Dashboard Visualizations",
    description:
      "Get the full picture before you even start chatting. Maps, heatmaps, and market summaries give you a data-rich launchpad.",
    bullets: [
      "Geographic housing summaries",
      "Maps + heat maps",
      "Track stocks you care about",
      "Preference-based views",
    ],
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="7" height="9" rx="1" />
        <rect x="14" y="3" width="7" height="5" rx="1" />
        <rect x="14" y="12" width="7" height="9" rx="1" />
        <rect x="3" y="16" width="7" height="5" rx="1" />
      </svg>
    ),
  },
];

const Features: React.FC = () => {
  return (
    <>
      <Navbar />
      <div className="features-page">

        {/* Ambient glow orbs */}
        <div className="feat-orb feat-orb--teal" aria-hidden="true" />
        <div className="feat-orb feat-orb--warm" aria-hidden="true" />

        <header className="features-header">
          <div className="features-eyebrow">PLATFORM OVERVIEW</div>
          <h1 className="features-hero-title">
            Two agents.<br />
            <span className="features-title-accent">One powerful platform.</span>
          </h1>
          <p>
            Virtual Economist delivers source-grounded insights across housing and stock markets —
            with personalization, session history, and dashboards built for quick decisions.
          </p>
        </header>

        <div className="features-grid">
          {features.map((f, i) => (
            <section
              key={f.id}
              className="feature-card"
              style={{
                "--accent": f.accent,
                "--delay": `${i * 60}ms`,
              } as React.CSSProperties}
            >
              <div className="feature-card-top">
                <div className="feature-icon-wrap">
                  {f.icon}
                </div>
                <span className="feature-tag">{f.tag}</span>
              </div>
              <h2>{f.title}</h2>
              <p>{f.description}</p>
              <ul className="feature-list">
                {f.bullets.map((b) => (
                  <li key={b}>
                    <span className="feature-list-dot" />
                    {b}
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      </div>
    </>
  );
};

export default Features;
