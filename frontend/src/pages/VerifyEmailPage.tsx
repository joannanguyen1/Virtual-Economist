import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Navbar from "../components/Navbar";
import { getAuthApiBase } from "../lib/api";
import "../styles/auth.css";

const VerifyEmailPage = () => {
  const [searchParams] = useSearchParams();
  const [message, setMessage] = useState("Verifying your email...");
  const [error, setError] = useState("");
  const AUTH_API = getAuthApiBase();

  useEffect(() => {
    const token = searchParams.get("token");
    if (!token) {
      setError("Missing verification token.");
      setMessage("");
      return;
    }

    const verify = async () => {
      try {
        const res = await fetch(
          `${AUTH_API}/api/verify-email?token=${encodeURIComponent(token)}`,
        );
        const contentType = res.headers.get("content-type") || "";
        const data = contentType.includes("application/json")
          ? await res.json()
          : {};

        if (!res.ok) {
          setError(data.error || "Verification failed.");
          setMessage("");
          return;
        }

        setMessage(data.message || "Email verified successfully.");
      } catch (err) {
        console.error(err);
        setError(`Can't reach the auth server at ${AUTH_API}.`);
        setMessage("");
      }
    };

    void verify();
  }, [AUTH_API, searchParams]);

  return (
    <>
      <Navbar />
      <div className="auth-container">
        <div className="auth-card">
          <p className="auth-eyebrow">Email verification</p>
          <h1>Confirm your account.</h1>
          {message ? <p className="auth-success-text">{message}</p> : null}
          {error ? <p className="auth-error">{error}</p> : null}
          <div className="auth-link-row">
            <Link className="auth-action-link" to="/login">
              Go to login
            </Link>
            <Link className="auth-secondary-link" to="/signup">
              Back to signup
            </Link>
          </div>
        </div>
      </div>
    </>
  );
};

export default VerifyEmailPage;
