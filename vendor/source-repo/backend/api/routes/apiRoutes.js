const express = require("express");
const router = express.Router();
const apiController = require("../controllers/apiController");
const authService = require("../services/authService");

const handleAuth = (req, res, next) => {
  const authHeader = req.headers["authorization"];
  if (!authHeader) {
    req.user = { userId: 'guest' };
    next();
  } else {
    authService.verifyToken(req, res, next);
  }
};

router.post("/", handleAuth, apiController.handleQuestion);

module.exports = router;
