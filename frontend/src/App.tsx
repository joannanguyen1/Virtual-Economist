import React from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import Dashboard from "./pages/Dashboard";
import HousingAgent from "./pages/HousingAgent";
import About from "./pages/About";
import MarketAgent from "./pages/MarketAgent";
import AssistantWorkspace from "./pages/AssistantWorkspace";
import VerifyEmailPage from "./pages/VerifyEmailPage";
import Features from "./pages/Features";

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/assistant" element={<AssistantWorkspace />} />
        <Route path="/verify-email" element={<VerifyEmailPage />} />
        <Route path="/housing" element={<HousingAgent />} />
        <Route path="/market" element={<MarketAgent />} />
        <Route path="/about" element={<About />} />
        <Route path="/features" element={<Features />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="*" element={<Navigate to="/assistant" replace />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;
