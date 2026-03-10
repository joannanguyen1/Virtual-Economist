import React from "react";
import { Navigate } from "react-router-dom";

const MarketAgent: React.FC = () => {
  return <Navigate to="/assistant?mode=market" replace />;
};

export default MarketAgent;
