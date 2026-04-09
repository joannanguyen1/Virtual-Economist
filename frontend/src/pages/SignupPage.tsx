import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import Navbar from "../components/Navbar";
import { getAuthApiBase } from "../lib/api";
import "../styles/auth.css";

const SignupPage = () => {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [verificationUrl, setVerificationUrl] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const navigate = useNavigate();
  const AUTH_API = getAuthApiBase();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSuccessMessage("");
    setVerificationUrl("");
    setIsSubmitting(true);

    try {
      const res = await fetch(`${AUTH_API}/api/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ name, email, password }),
      });

      const contentType = res.headers.get("content-type") || "";
      const data = contentType.includes("application/json")
        ? await res.json()
        : {};

      if (!res.ok) {
        setError(data.error || "Signup failed");
        return;
      }

      setSuccessMessage(
        data.message || "Signup successful. Verify your email before logging in.",
      );
      setVerificationUrl(data.verificationUrl || "");

    } catch (err) {
      console.error(err);
      setError(`Can't reach the auth server at ${AUTH_API}.`);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <>
      <Navbar />
      <div className="auth-container">
        <div className="auth-card">
          <p className="auth-eyebrow">Create account</p>
          <h1>Start saving city and market research in one place.</h1>

          <form className="auth-form" onSubmit={handleSubmit}>
            <input
              type="text"
              placeholder="Full Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />

            <input
              type="email"
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />

            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />

            {error ? <p className="auth-error">{error}</p> : null}
            {successMessage ? (
              <div className="auth-success">
                <p>{successMessage}</p>
                {verificationUrl ? (
                  <a className="auth-action-link" href={verificationUrl}>
                    Verify email now
                  </a>
                ) : null}
                <button
                  type="button"
                  className="auth-secondary-button"
                  onClick={() => navigate("/login")}
                >
                  Go to login
                </button>
              </div>
            ) : null}

            <button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Creating account..." : "Sign Up"}
            </button>
          </form>

          <p className="auth-footer">
            Already have an account? <Link to="/login">Log in</Link>
          </p>
        </div>
      </div>
    </>
  );
};

export default SignupPage;
