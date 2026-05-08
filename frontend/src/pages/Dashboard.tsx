import React from "react";
import { useNavigate } from "react-router-dom";
import Navbar from "../components/Navbar";
import "../styles/dashboard.css";
import WatchlistCard from "../components/WatchlistCard";
import HousingHeatmap from "../components/HousingHeatmap";
import { allowedAgentModes, getStoredUser } from "../lib/auth";

const Dashboard: React.FC = () => {
  const navigate = useNavigate();

  const user = getStoredUser();
  const allowedModes = allowedAgentModes(user?.role);
  const canSeeHousing = allowedModes.includes("housing");
  const canSeeMarket = allowedModes.includes("market");
  const canSeeAuto = allowedModes.includes("auto");

  const workspaces = [
    {
      id: "assistant",
      name: "Unified Assistant",
      description:
        "Ask one question and let the app route across housing, city economics, weather, stocks, and macro data in a single workspace.",
      eyebrow: "Recommended",
      route: "/assistant",
      enabled: canSeeAuto,
    },
    {
      id: "housing",
      name: "Housing Focus",
      description:
        "Pin the assistant to home values, inventory, rents, affordability, incomes, and weather across U.S. cities.",
      eyebrow: "Pinned mode",
      route: "/assistant?mode=housing",
      enabled: canSeeHousing,
    },
    {
      id: "market",
      name: "Market Focus",
      description:
        "Pin the assistant to stock quotes, analyst recommendations, sector screens, and macro indicators.",
      eyebrow: "Pinned mode",
      route: "/assistant?mode=market",
      enabled: canSeeMarket,
    },
  ];

  const visibleWorkspaces = workspaces.filter((w) => w.enabled);

  return (
    <>
      <Navbar />
      <main className="dashboard-page">
        <div className="dashboard-orb dashboard-orb--teal" aria-hidden="true" />
        <div className="dashboard-orb dashboard-orb--warm" aria-hidden="true" />
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
            {canSeeHousing ? (
              <button
                type="button"
                className="dashboard-secondary-button"
                onClick={() => navigate("/assistant?mode=housing")}
              >
                Start with housing
              </button>
            ) : null}
          </div>
        </section>

        {canSeeMarket ? <WatchlistCard /> : null}

        {canSeeHousing ? (
          <section className="dashboard-overview">
            <div className="dashboard-panel">
              <h2>Housing heatmap</h2>
              <p className="dashboard-muted">
                Search a city/state, then pan/zoom to change the selected region.
                Metrics may not be up-to-date for all locations.
              </p>
              <HousingHeatmap />
            </div>
          </section>
        ) : null}

        <section className="agents-grid">
          {visibleWorkspaces.map((workspace) => (
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
