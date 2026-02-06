import React from "react";
import Navbar from "../components/Navbar";
import ChatInterface from "../components/ChatInterface";
import "../styles/dashboard.css"; // reusing dashboard layout for container

const HousingAgent: React.FC = () => {
  return (
    <>
      <Navbar />
      <div className="dashboard"> {/* Reusing dashboard container styles */}
        <ChatInterface agentName="Housing & City Agent" />
      </div>
    </>
  );
};

export default HousingAgent;
