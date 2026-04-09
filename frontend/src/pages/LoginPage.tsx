import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import Navbar from "../components/Navbar";
import { getAuthApiBase } from "../lib/api";
import { setAuthSession } from "../lib/auth";
import "../styles/auth.css";

const LoginPage = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [verificationUrl, setVerificationUrl] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const navigate = useNavigate();
  const AUTH_API = getAuthApiBase();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setVerificationUrl("");
    setIsSubmitting(true);

    try {
      const res = await fetch(`${AUTH_API}/api/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, password }),
      });

      const contentType = res.headers.get("content-type") || "";
      const data = contentType.includes("application/json")
        ? await res.json()
        : {};

      if (!res.ok) {
        setError(data.error || "Invalid credentials");
        setVerificationUrl(data.verificationUrl || "");
        return;
      }

      setAuthSession(data.token, data.user);
      navigate("/assistant");

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
          <p className="auth-eyebrow">Virtual Economist account</p>
          <h1>Log in to save chats and reopen past threads.</h1>

          <form className="auth-form" onSubmit={handleSubmit}>
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
            {verificationUrl ? (
              <div className="auth-link-row">
                <a className="auth-action-link" href={verificationUrl}>
                  Verify email now
                </a>
              </div>
            ) : null}

            <button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Logging in..." : "Log In"}
            </button>
          </form>

          <p className="auth-footer">
            Don’t have an account? <Link to="/signup">Sign up</Link>
          </p>
        </div>
      </div>
    </>
  );
};

export default LoginPage;
