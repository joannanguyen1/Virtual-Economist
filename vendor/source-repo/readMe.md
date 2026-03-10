# 📊 Virtual Economists

Virtual Economists is a chat-based web application featuring two AI-powered agents:

- A **Housing/City Agent** that helps users understand U.S. cities through real estate and weather data.
- A **Stock/Market Agent** that helps users explore financial data, analyst recommendations, and institutional/insider ownership.

---

## 🔧 Project Overview

**What it does**:
Two AI agents answer questions related to either U.S. housing/city information or stock/market data using natural language.

**Main Use Case**:
Allows users to gain insights into U.S. cities (e.g., home prices, weather) or make smarter investing decisions through semantic and keyword-based queries.

---

## 🧠 Core Features

- Chat interface with agent-switching
- Natural language to SQL query conversion via OpenAI
- Semantic search with fuzzy matching
- User login and chat history
- Embedding-based retrieval for housing and stock datasets

---

## 📦 Tech Stack

| Layer     | Tech                                |
| --------- | ----------------------------------- |
| Frontend  | TypeScript                          |
| Backend   | Python                              |
| AI Models | OpenAI GPT (chat, query generation) |
| Database  | PostgreSQL (with pgvector, jsonb)   |
| Hosting   | AWS                                 |

---

## 🗂️ Architecture

- Frontend and backend are separated.
- Backend connects to AWS-hosted PostgreSQL.
- Chatbot UI allows real-time interaction.
- No microservices or pipelines.
- Backend must be running before frontend is usable.

---

## 💬 LLM Integration

### 🏘 Housing/City Agent — Example Questions

- _Which cities have home values between $150,000 and $300,000 and mild summers with average temperatures around 75°F?_
- _Show me the wind and precipitation in Philadelphia, PA for August-2024._
- _What is the average snowfall and temperature like in Philadelphia, PA during the winter?_

### 📈 Stock/Market Agent — Example Questions

- _Can you provide me with stocks in the health sector that analysts recommend buying?_
- _Show me stocks across sectors with high institutional ownership and low insider ownership._

**Processing**:
Natural language is converted to SQL using OpenAI. Embeddings help with semantic context and similarity search.

---

## 🗄️ Database Schema

### `housing_data_embeddings`

| Column     | Type         | Notes                          |
| ---------- | ------------ | ------------------------------ |
| id         | integer      | Primary Key                    |
| embedding  | vector(1536) | OpenAI embedding vector        |
| metadata   | jsonb        | Housing & weather data by city |
| created_at | timestamp    | Creation timestamp             |

**metadata** includes:

- `city`, `median_home_value`, `median_household_income`
- `weather_by_month`:
  - `avg_temperature_f`, `min_temperature_f`, `max_temperature_f`
  - `precipitation_in`, `windspeed_mph`, `snowfall_in`

---

### `embeddings` (for stock agent)

| Column        | Type         | Notes                      |
| ------------- | ------------ | -------------------------- |
| id            | integer      | Primary Key                |
| vector_column | vector(1536) | OpenAI embedding vector    |
| text          | text         | Source document or summary |
| metadata      | jsonb        | Stock metadata             |

**metadata** includes:

- `name`, `sector`, `industry`, `recommendation`
- `insider_ownership`, `institutional_ownership`

---

### `users`

| Field       | Type                  |
| ----------- | --------------------- |
| id          | integer               |
| user_name   | varchar(100)          |
| email       | varchar(255) (unique) |
| hashed_pass | text                  |

---

### `chats`

Tracks conversations per user.

### `messages`

Stores user/bot messages, timestamps, and chat context.

---

## 🔎 Search & Retrieval

- Embedding-based semantic search via OpenAI
- Keyword filters via SQL
- Fuzzy city name matching with `pg_trgm`:

  ```sql
  WHERE similarity(metadata->>'city', '<user input>') > 0.3
  ```

## 👤 User Interaction

Users interact via a clean, chatbot-style web interface.

The app provides a toggle to switch between:

- 🏘 **Housing/City Agent**
- 📈 **Stock/Market Agent**

**Authentication is required:**

- Users must log in before using either agent.
- Each user has a unique chat history.

## 🚀 Deployment

**Current Status**: Not yet deployed publicly.

**Hosting Plan**: AWS (PostgreSQL DB already hosted)

**Environment Variables Needed**:

- `OPENAI_API_KEY` – for embedding generation and natural language processing
- `JWT_SECRET_KEY` – for user authentication
- AWS environment configs for connecting to the PostgreSQL instance

## 🛠️ Developer Notes

To run the project locally:

### 1. Install Dependencies

**Backend:**

```bash
cd backend/api
pip install -r requirements.txt
npm install

```

**Run the Application:**

```bash
cd backend/api
npm start

cd frontend
npm start
```

## ✅ Unit Testing

To ensure code quality and reliability, we have implemented unit testing for key components of the application. Our tests are written using Jest for backend testing. Below are the steps to run the tests:

### 1. Install Testing Dependencies

**Backend:**

Make sure to install Jest and other testing dependencies:

```bash
cd backend/api
npm install --save-dev jest supertest
```

### 2. Run the Unit Tests:

**Run a specific test file:**

```bash
npx jest tests/[example_.test.js]
```

### 3. View Test Results

After running the tests, you will see a summary of passed and failed test cases. Detailed information about each test case can be found in the test log.
