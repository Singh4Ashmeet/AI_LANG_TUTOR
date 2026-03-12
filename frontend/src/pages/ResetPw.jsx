import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";
import styles from "./ResetPw.module.css";

const ResetPw = () => {
  const navigate = useNavigate();
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    setStatus("");
    try {
      const verify = await api.post("/auth/password/verify-reset", { code });
      await api.post("/auth/password/reset", { new_password: password }, { token: verify.reset_token });
      setStatus("Password updated. Please log in.");
      setTimeout(() => navigate("/login"), 1200);
    } catch (err) {
      setError(err.message || "Unable to reset password.");
    }
  };

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <h2>Enter reset code</h2>
        <p>Use the OTP email to reset your password.</p>
        {error && <div className={styles.error}>{error}</div>}
        {status && <div className={styles.status}>{status}</div>}
        <form onSubmit={submit} className={styles.form}>
          <input value={code} onChange={(event) => setCode(event.target.value)} placeholder="OTP code" />
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="New password"
          />
          <button type="submit">Reset password</button>
        </form>
      </div>
    </div>
  );
};

export default ResetPw;

