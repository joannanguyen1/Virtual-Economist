import React from "react";
import { Link, useLocation } from "react-router-dom";
import "../styles/navbar.css";

const Navbar: React.FC = () => {
  const location = useLocation();
  const isLanding = location.pathname === "/";

  return (
    <nav className="navbar">
      <Link to="/" className="navbar-brand" style={{ color: 'white', textDecoration: 'none' }}>
        Virtual Economist
      </Link>
      <div className="navbar-links">
        {isLanding ? (
          <>
            <a href="#features">Features</a>
            <a href="#about">About</a>
            <Link to="/login">Login</Link>
          </>
        ) : (
          <>
            <Link to="/dashboard">Dashboard</Link>
            <Link to="/housing">Housing</Link>
            <Link to="/market">Market</Link>
          </>
        )}
      </div>
    </nav>
  );
};

export default Navbar;
