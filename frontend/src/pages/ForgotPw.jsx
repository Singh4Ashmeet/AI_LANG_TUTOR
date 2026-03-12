import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";
import styles from "./ForgotPw.module.css";

const ForgotPw = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setStatus("");
    try {
      await api.post("/auth/password/request-reset", { email });
      setStatus("If the account exists, an OTP has been sent.");
    } catch (err) {
      setError(err.message || "Unable to request reset.");
    }
  };

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <h2>Reset your password</h2>
        <p>We will send a verification code to your email.</p>
        {error && <div className={styles.error}>{error}</div>}
        {status && <div className={styles.status}>{status}</div>}
        <form onSubmit={handleSubmit} className={styles.form}>
          <input type="email" placeholder="Email" value={email} onChange={(event) => setEmail(event.target.value)} />
          <button type="submit">Send code</button>
        </form>
        <button type="button" className={styles.link} onClick={() => navigate("/reset-password")}>
          I already have a code
        </button>
      </div>
    </div>
  );
};

export default ForgotPw;

