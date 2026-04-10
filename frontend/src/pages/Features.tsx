import React from "react";
import Navbar from "../components/Navbar";
import "../styles/features.css";


const Features: React.FC = () => {
  return (
    <div className="features-page">
      <header className="features-header">
        <h1>Features</h1>
        <p>
          Virtual Economist is a dual-agent AI platform that delivers source-grounded
          insights across the housing market and stock market, with personalization,
          session history, and dashboards built for quick decision-making.
        </p>
      </header>

      <div className="features-grid">
        <section className="feature-card">
          <div className="feature-icon">🏠</div>
          <h2>Housing / City Agent</h2>
          <p>
            Ask about home values, rent affordability, market inventory, and local conditions.
            Get city-specific insights using structured housing and income data, plus
            geographic + weather context.
          </p>
          <ul className="feature-list">
            <li>Home values & rent trend analysis</li>
            <li>Inventory & market speed indicators</li>
            <li>Affordability using income estimates</li>
            <li>Location-aware context (maps/weather)</li>
          </ul>
        </section>

        <section className="feature-card">
          <div className="feature-icon">📈</div>
          <h2>Stock Agent</h2>
          <p>
            Explore market performance, sector movement, and sentiment signals. Designed to
            summarize complex market information into clear, actionable insights.
          </p>
          <ul className="feature-list">
            <li>Historical ticker trends and movement</li>
            <li>Sector performance summaries</li>
            <li>News sentiment and market context</li>
            <li>Market overview + explainable insights</li>
          </ul>
        </section>

        <section className="feature-card">
          <div className="feature-icon">✅</div>
          <h2>Source-Grounded Answers</h2>
          <p>
            Built to minimize hallucinations by grounding responses in valid data sources.
            The goal is to provide verifiable, trustworthy outputs for users.
          </p>
          <ul className="feature-list">
            <li>Data-backed responses (not guesswork)</li>
            <li>Clear, structured explanations</li>
            <li>Consistency across sessions</li>
          </ul>
        </section>

        <section className="feature-card">
          <div className="feature-icon">🔐</div>
          <h2>Accounts & Personalization</h2>
          <p>
            Create an account, log in, and get a more personalized experience over time.
            Preferences and chat context enable more relevant responses.
          </p>
          <ul className="feature-list">
            <li>Login + signup flow</li>
            <li>User profile & preferences</li>
            <li>Personalized dashboard scope</li>
          </ul>
        </section>

        <section className="feature-card">
          <div className="feature-icon">🕘</div>
          <h2>Chat History & Search</h2>
          <p>
            Save sessions so you don’t have to repeat prompts. Quickly search previous chats
            to retrieve context and prior insights.
          </p>
          <ul className="feature-list">
            <li>Session history</li>
            <li>Searchable chat archive</li>
            <li>Conversation context support</li>
          </ul>
        </section>

        <section className="feature-card">
          <div className="feature-icon">🗺️</div>
          <h2>Dashboard Visualizations</h2>
          <p>
            A fast snapshot of trends before you chat: maps and heatmaps for housing, plus
            stock tracking and market summaries.
          </p>
          <ul className="feature-list">
            <li>Geographic housing summaries</li>
            <li>Maps + heat maps</li>
            <li>Track stocks you care about</li>
            <li>Preference-based views</li>
          </ul>
        </section>
      </div>
    </div>
  );
};

export default Features;
