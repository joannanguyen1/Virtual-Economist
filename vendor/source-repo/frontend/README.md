# Virtual Economists - Frontend

> The Frontend of **Virtual Economists** is a TypeScript-based web application that powers the user interface for interacting with two AI agents:
>
> - **Housing/City Agent:** Provides insights into U.S. cities using real estate and weather data.
> - **Stock/Market Agent:** Helps users explore financial data, including analyst recommendations and ownership details.

---

## 🚀 Project Overview

**What it does:**

- Presents a chatbot-style UI allowing users to query two distinct AI agents.
- Supports seamless switching between agents.
- Manages user authentication and retrieves session-based chat history.

**Main Use Case:**
Users can interact in natural language to visualize data about U.S. cities or financial markets, gaining insights without needing to navigate complex dashboards.

---

## ✨ Core Features

- **Chatbot Interface:** Clean, responsive conversation layout.
- **Agent Toggle:** Switch between Housing/City and Stock/Market agents.
- **Authentication:** Secure login with session persistence.
- **Chat History:** Load and display past conversations.
- **API Integration:** Communicates with backend services for data retrieval.

---

## 📁 Folder Structure

```
frontend/
├── public/            # Static assets (HTML, images, etc.)
├── src/               # Frontend source code
│   ├── components/    # Reusable UI components
│   ├── pages/         # Individual application pages
│   ├── styles/        # CSS & styling files
│   ├── utils/         # Helper functions and hooks
│   └── App.tsx        # Main application entry point
├── package.json       # Project metadata & dependencies
├── tsconfig.json      # TypeScript configuration
└── .gitignore         # Files ignored by Git
```

---

## 🛠 Getting Started

1. **Clone the repository**
   git clone https://github.com/DU-Virtual-Economist/Virtual-Economist.git

2. **Navigate to the frontend folder**
   cd Virtual-Economist/frontend

3. **Install dependencies**
   npm install

4. **Start the development server**
   npm start

> **Note:** Ensure the backend API is running and accessible.

---
