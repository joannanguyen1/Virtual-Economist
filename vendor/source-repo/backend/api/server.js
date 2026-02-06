// server.js
const express = require("express");
const bodyParser = require("body-parser");
const cors = require("cors");
const authRoutes = require("./routes/authRoutes");
const apiRoutes = require("./routes/apiRoutes");
const chatRoutes = require("./routes/chatHistoryRoutes");

const app = express();
const port = 8000;

// Middleware
app.use(express.json());
app.use(bodyParser.json());
app.use(cors());
// Routes
app.use("/auth", authRoutes);
app.use("/api", apiRoutes);
app.use("/chatHistory", chatRoutes);

// Start the server
app.listen(port, () => {
  console.log(`Server is running on http://localhost:${port}`);
});
