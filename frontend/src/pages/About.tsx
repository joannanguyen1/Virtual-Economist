import React from 'react';
import { useNavigate } from "react-router-dom";
import Navbar from "../components/Navbar";
import "../styles/about.css";

const About: React.FC = () => {
  return (
    <div className="about-page">
      <h1>About Virtual Economist</h1>
      <p>
        Virtual Economist is a comprehensive AI-powered platform that provides
        insights into economic data, with a focus on the housing market and stock
        market trends. Our AI agents analyze a variety of data sources to offer
        real-time, personalized answers to user inquiries. The platform supports
        users with tailored housing and stock recommendations, helping them make
        informed decisions in today's fast-changing market landscape.
      </p>
      <h2>Our Mission</h2>
      <p>
        Our mission is to make economic data accessible and understandable to
        everyone. By leveraging advanced AI technologies and real-time data, we
        aim to provide actionable insights to guide users through housing market
        decisions and stock investments.
      </p>
      <h2>Technology Stack</h2>
      <ul>
        <li>Frontend: React, TypeScript</li>
        <li>Backend: Python, FastAPI, Langchain</li>
        <li>Database: PostgreSQL, pgvector</li>
        <li>Data APIs: Zillow, U.S. Census Bureau, OpenWeatherAPI</li>
      </ul>
    </div>
  );
};

export default About;