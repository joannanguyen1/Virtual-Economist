import React from "react";
import { useNavigate } from "react-router-dom";
import Navbar from "../components/Navbar";
import "../styles/dashboard.css";

const Dashboard: React.FC = () => {
  const navigate = useNavigate();

  const agents = [
    {
      id: "housing",
      name: "Housing & City Agent",
      description:
        "Analyze real estate trends, cost of living, weather data, and income statistics across various U.S. cities to find your perfect place.",
      icon: "🏘️",
      route: "/housing",
    },
    {
      id: "market",
      name: "Stock & Market Agent",
      description:
        "Get insights on stock performance, analyst recommendations, insider ownership, and sector trends to make informed investment decisions.",
      icon: "📈",
      route: "/market",
    },
  ];

  return (
    <>
      <Navbar />
      <div className="dashboard">
        <header className="dashboard-header">
          <h1>Welcome to Virtual Economist</h1>
          <p>Select an intelligent agent to start your analysis</p>
        </header>

        <div className="agents-grid">
          {agents.map((agent) => (
            <div
              key={agent.id}
              className="agent-card"
              onClick={() => navigate(agent.route)}
            >
              <div className="agent-icon">{agent.icon}</div>
              <h2>{agent.name}</h2>
              <p>{agent.description}</p>
              <span className="agent-link">
                Launch Agent <span>→</span>
              </span>
            </div>
          ))}
        </div>
      </div>
    </>
  );
};

export default Dashboard;
