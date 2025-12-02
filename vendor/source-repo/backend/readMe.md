# Backend for Economic Chatbot  

This backend project provides the functionality for a chatbot that answers economic questions by leveraging datasets and natural language processing.  

---

## 🔌 API Reference

All endpoints are under `http://localhost:8000` and expect a JSON request/response.  
Authenticated routes require a valid JWT in the `Authorization: Bearer <token>` header.

### Authentication

| Method | Path               | Body                                  | Description                         |
| ------ | ------------------ | ------------------------------------- | ---------------------------------   |
| POST   | `/auth/signup`     | `{ "username", "password", "email" }` | Create a new user and return a JWT. |
| POST   | `/auth/login`      | `{ "username", "password" }`          | Authenticate user and return a JWT. |
| POST   | `/auth/logout`     | `{ "token" }`                         | (Optional) Invalidate a token.      |

### Chat

| Method | Path    | Body                                                                                       | Description                                                                                 |
| ------ | ------- | ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------- |
| POST   | `/api`  | `{ "question": string, "agentSelection": { "stockAgent": boolean, "housingAgent": boolean }, "chatId": integer }` | Send a question to the chosen AI agent; returns `{ answer: string }`.|

### Chat History

| Method | Path                           | Body                                                        | Description                                                                        |
| ------ | ------------------------------ | ----------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| POST   | `/chatHistory/create`          | — (no body)                                                 | Create a new chat for the current user; returns chat metadata.                     |
| POST   | `/chatHistory/add/:chatId`     | `{ "message": string, "isClient": boolean }`                | Add a message (user or bot) to the specified chat; returns the new message record. |
| GET    | `/chatHistory/history/:chatId` | —                                                           | Retrieve all messages for a single chat.                                           |
| GET    | `/chatHistory/history`         | —                                                           | Retrieve metadata and first-class list of all chats for the current user.          |
| DELETE | `/chatHistory/history/:chatId` | —                                                           | Delete a chat and its messages.                                                    |

---

## Requirements  

### Prerequisites  
Before running the application, ensure you have the following:  
- **Python 3.12**
- `pip` (Python package installer) available.  

### Dependencies  
The required Python packages are listed in the `requirements.txt` file.  

To install the dependencies:  
1. Open a terminal and navigate to the `backend` folder.  
2. Run the following command:  
   ```bash  
   pip install -r requirements.txt
### Running backend
1. Navigate to the backend/app folder in your terminal.
2. Run the application using `python main.py`
