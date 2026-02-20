import React from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import Dashboard from "./pages/Dashboard";
import HousingAgent from "./pages/HousingAgent";
import MarketAgent from "./pages/MarketAgent";

const App: React.FC = () => {
  return (
    <BrowserRouter>
    <Routes>
        <Route path="/" element = {<LandingPage />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/housing" element={<HousingAgent />} />
        <Route path="/market" element={<MarketAgent />} />
        <Route path="/login" element = {<LoginPage />} />
        <Route path="/signup" element = {<SignupPage />} />
    </Routes>
    </BrowserRouter>
  )
};

export default App;
