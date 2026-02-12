import React from "react";
import { useNavigate } from "react-router-dom";
import Navbar from "../components/Navbar";
import "../styles/landing.css";

const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  return (
    <>
      <Navbar />
      <div className="landing">
        <header className="landing-header">
          <h1>Virtual Economist</h1>
          <p>
            Data-driven Agents for housing, cost of living, and economic
            trends.
          </p>
          <div className="landing-actions">
            <button className="primary" onClick={() => navigate("/dashboard")}>Get Started</button>
            <button className="secondary">Learn More</button>
          </div>
        </header>
      </div>
    </>
  );
};

export default LandingPage;
