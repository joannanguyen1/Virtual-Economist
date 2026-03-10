import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

export default function VerifyEmail() {
  const [params] = useSearchParams();
  const token = params.get("token");

  const [status, setStatus] = useState<"idle" | "loading" | "ok" | "error">("idle");
  const [msg, setMsg] = useState("");

  useEffect(() => {
    async function run() {
      if (!token) {
        setStatus("error");
        setMsg("Missing verification token.");
        return;
      }

      setStatus("loading");
      try {
        const res = await fetch(
          `${process.env.REACT_APP_API_URL}/api/verify-email?token=${encodeURIComponent(token)}`
        );
        const data = await res.json().catch(() => ({}));

        if (!res.ok) {
          setStatus("error");
          setMsg(data.error || "Verification failed.");
          return;
        }

        setStatus("ok");
        setMsg(data.message || "Email verified! You can now log in.");
      } catch {
        setStatus("error");
        setMsg("Server error verifying email.");
      }
    }
    run();
  }, [token]);

  return (
    <div className="auth-container">
      <h1>Email Verification</h1>

      {status === "loading" && <p>Verifying...</p>}
      {status === "error" && <p>{msg}</p>}
      {status === "ok" && (
        <>
          <p>{msg}</p>
          <p>
            <Link to="/login">Go to login</Link>
          </p>
        </>
      )}
    </div>
  );
}