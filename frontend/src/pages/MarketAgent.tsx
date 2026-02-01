import React from "react";
import Navbar from "../components/Navbar";
import ChatInterface from "../components/ChatInterface";
import "../styles/dashboard.css";

const MarketAgent: React.FC = () => {
  return (
    <>
      <Navbar />
      <div className="dashboard">
        <ChatInterface agentName="Stock & Market Agent" />
      </div>
    </>
  );
};

export default MarketAgent;
