import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import LandingPage from "./pages/LandingPage";
import Dashboard from "./pages/Dashboard";
import HousingAgent from "./pages/HousingAgent";
import MarketAgent from "./pages/MarketAgent";

const App: React.FC = () => {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/housing" element={<HousingAgent />} />
        <Route path="/market" element={<MarketAgent />} />
      </Routes>
    </Router>
  );
};

export default App;
