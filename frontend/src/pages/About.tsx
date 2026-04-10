import React from "react";
import Navbar from "../components/Navbar";
import "../styles/about.css";

const stack = [
  {
    label: "Frontend",
    value: "React, TypeScript",
    accent: "#2fb6a3",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="16 18 22 12 16 6" />
        <polyline points="8 6 2 12 8 18" />
      </svg>
    ),
  },
  {
    label: "Backend",
    value: "Python, FastAPI, Langchain",
    accent: "#f4b35f",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
        <rect x="2" y="3" width="20" height="14" rx="2" />
        <line x1="8" y1="21" x2="16" y2="21" />
        <line x1="12" y1="17" x2="12" y2="21" />
      </svg>
    ),
  },
  {
    label: "Database",
    value: "PostgreSQL, pgvector",
    accent: "#35d1c5",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
        <ellipse cx="12" cy="5" rx="9" ry="3" />
        <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
        <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
      </svg>
    ),
  },
  {
    label: "Data APIs",
    value: "Zillow, U.S. Census Bureau, OpenWeatherAPI",
    accent: "#f4b35f",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" />
        <line x1="2" y1="12" x2="22" y2="12" />
        <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10A15.3 15.3 0 0 1 12 2z" />
      </svg>
    ),
  },
];

const stats = [
  { value: "2", label: "Specialized AI Agents" },
  { value: "4+", label: "Live Data Sources" },
  { value: "Real-time", label: "Market Insights" },
];

const About: React.FC = () => {
  return (
    <>
      <Navbar />
      <div className="about-page">

        <div className="about-orb about-orb--teal" aria-hidden="true" />
        <div className="about-orb about-orb--warm" aria-hidden="true" />

        {/* Hero */}
        <header className="about-header">
          <div className="about-eyebrow">THE PROJECT</div>
          <h1 className="about-hero-title">
            Built for the way people{" "}
            <span className="about-title-accent">actually make decisions.</span>
          </h1>
          <p>
            Virtual Economist is an AI-powered platform that delivers source-grounded insights
            into housing and stock markets — personalized, fast, and built on real data.
          </p>
        </header>

        {/* Stats bar */}
        <div className="about-stats">
          {stats.map((s) => (
            <div key={s.label} className="about-stat">
              <span className="about-stat-value">{s.value}</span>
              <span className="about-stat-label">{s.label}</span>
            </div>
          ))}
        </div>

        <div className="about-body">

          {/* Mission */}
          <section className="about-section about-mission">
            <div className="about-section-inner">
              <div className="about-section-label">OUR MISSION</div>
              <h2>Making economic data accessible to everyone</h2>
              <p>
                Most financial platforms are built for experts. We built Virtual Economist for
                everyone else. By combining advanced AI with real-time data, we translate
                complex market signals into plain-English insights — so you can make confident
                housing and investment decisions without needing a finance degree.
              </p>
            </div>
            <div className="about-mission-glow" aria-hidden="true" />
          </section>

          {/* Stack */}
          <section className="about-section">
            <div className="about-section-label">TECHNOLOGY STACK</div>
            <h2>Modern infrastructure, built to scale</h2>
            <div className="about-stack-grid">
              {stack.map((item, i) => (
                <div
                  key={item.label}
                  className="about-stack-card"
                  style={{
                    "--accent": item.accent,
                    "--delay": `${i * 70}ms`,
                  } as React.CSSProperties}
                >
                  <div className="about-stack-icon">{item.icon}</div>
                  <div>
                    <span className="about-stack-label">{item.label}</span>
                    <span className="about-stack-value">{item.value}</span>
                  </div>
                </div>
              ))}
            </div>
          </section>

        </div>
      </div>
    </>
  );
};

export default About;
