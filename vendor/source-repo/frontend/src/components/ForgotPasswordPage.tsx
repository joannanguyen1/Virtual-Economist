import React from "react";
import { Link } from "react-router-dom";
import "./ForgotPasswordPage.css";

const ForgotPasswordPage: React.FC = () => {
  return (
    <div className="forgot-password-container">
      <h2>Forgot Password</h2>
      <p>
        Please enter your email address, and we'll send you instructions to
        reset your password.
      </p>
      <form>
        <input
          type="email"
          placeholder="Email address"
          className="forgot-password-input"
        />
        <button type="submit" className="forgot-password-submit">
          Submit
        </button>
      </form>
      <p>
        Remembered your password?{" "}
        <Link to="/login" className="login-link">
          Log In
        </Link>
      </p>
    </div>
  );
};

export default ForgotPasswordPage;
