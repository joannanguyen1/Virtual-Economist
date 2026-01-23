import React from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";

const App: React.FC = () => {
  return (
    <BrowserRouter>
    <Routes>
        <Route path="/" element = {<LandingPage />} />
        <Route path="/login" element = {<LoginPage />} />
        <Route path="/signup" element = {<SignupPage />} />
    </Routes>
    </BrowserRouter>
  )
};

export default App;
