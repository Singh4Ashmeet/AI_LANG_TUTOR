import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import styles from "./TotpVerify.module.css";

const TotpVerify = () => {
  const navigate = useNavigate();
  const { verifyTotp } = useAuth();
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (code.trim().length !== 6) {
      setError("Enter the 6-digit authenticator code.");
      return;
    }
    setError("");
    setIsSubmitting(true);
    try {
      const user = await verifyTotp(code.trim());
      if (user.role === "admin") {
        navigate("/admin");
      } else if (!user.onboarding_complete) {
        navigate("/onboarding");
      } else {
        navigate("/dashboard");
      }
    } catch (err) {
      setError(err.message || "Invalid code.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <h2>Authenticator code</h2>
        <p>Open your authenticator app to continue.</p>
        {error && <div className={styles.error}>{error}</div>}
        <form onSubmit={handleSubmit} className={styles.form}>
          <input
            value={code}
            onChange={(event) => setCode(event.target.value)}
            placeholder="6-digit code"
            inputMode="numeric"
          />
          <button type="submit" disabled={isSubmitting}>
            Verify
          </button>
        </form>
      </div>
    </div>
  );
};

export default TotpVerify;

