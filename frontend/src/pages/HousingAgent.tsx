import React from "react";
import { Navigate } from "react-router-dom";

const HousingAgent: React.FC = () => {
  return <Navigate to="/assistant?mode=housing" replace />;
};

export default HousingAgent;
