import React from "react";
import { useNavigate } from "react-router-dom";
import Navbar from "../components/Navbar";
import "../styles/dashboard.css";
import WatchlistCard from "../components/WatchlistCard";

const Dashboard: React.FC = () => {
  const navigate = useNavigate();

  const workspaces = [
    {
      id: "assistant",
      name: "Unified Assistant",
      description:
        "Ask one question and let the app route across housing, city economics, weather, stocks, and macro data in a single workspace.",
      eyebrow: "Recommended",
      route: "/assistant",
    },
    {
      id: "housing",
      name: "Housing Focus",
      description:
        "Pin the assistant to home values, inventory, rents, affordability, incomes, and weather across U.S. cities.",
      eyebrow: "Pinned mode",
      route: "/assistant?mode=housing",
    },
    {
      id: "market",
      name: "Market Focus",
      description:
        "Pin the assistant to stock quotes, analyst recommendations, sector screens, and macro indicators.",
      eyebrow: "Pinned mode",
      route: "/assistant?mode=market",
    },
  ];

  return (
    <>
      <Navbar />
      <main className="dashboard-page">
        <section className="dashboard-hero">
          <p className="dashboard-eyebrow">Unified research workflow</p>
          <h1>One assistant, two specialties, one cleaner interface.</h1>
          <p>
            Start in auto mode for most questions. Pin housing or market mode
            only when you want tighter routing for that domain.
          </p>

          <div className="dashboard-actions">
            <button
              type="button"
              className="dashboard-primary-button"
              onClick={() => navigate("/assistant")}
            >
              Open assistant
            </button>
            <button
              type="button"
              className="dashboard-secondary-button"
              onClick={() => navigate("/assistant?mode=housing")}
            >
              Start with housing
            </button>
          </div>
        </section>
        <WatchlistCard />
        <section className="agents-grid">
          {workspaces.map((workspace) => (
            <div
              key={workspace.id}
              className="agent-card"
              onClick={() => navigate(workspace.route)}
            >
              <p className="agent-eyebrow">{workspace.eyebrow}</p>
              <h2>{workspace.name}</h2>
              <p>{workspace.description}</p>
              <span className="agent-link">
                Open workspace <span>→</span>
              </span>
            </div>
          ))}
        </section>
      </main>
    </>
  );
};

export default Dashboard;
