import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext.jsx";
import styles from "./AdminLogin.module.css";

const AdminLogin = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      await login(email, password);
      navigate("/login/otp");
    } catch (err) {
      setError(err.message || "Unable to sign in.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className={styles.page}>
      <div className={styles.layout}>
        <div className={styles.card}>
          <div className={styles.heading}>
            <span className={styles.pill}>LinguAI Admin</span>
            <h1>Administrator access</h1>
            <p>Secure login for the control center.</p>
          </div>
          {error && <div className={styles.error}>{error}</div>}
          <form onSubmit={submit} className={styles.form}>
            <label>
              Email
              <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
            </label>
            <label>
              Password
              <div className={styles.passwordField}>
                <input
                  className={styles.passwordInput}
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  required
                />
                <button
                  type="button"
                  className={styles.passwordToggle}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  onClick={() => setShowPassword((value) => !value)}
                >
                  <span>{showPassword ? "Shield" : "Reveal"}</span>
                </button>
              </div>
            </label>
            <button type="submit" disabled={isSubmitting}>
              Continue
            </button>
          </form>
        </div>
        <aside className={styles.workflow}>
          <div className={styles.workflowTitle}>Data workflow</div>
          <div className={styles.workflowItem}>
            <strong>1. Learner activity</strong>
            <span>Lessons, chat, roleplay, and practice generate structured session records.</span>
          </div>
          <div className={styles.workflowItem}>
            <strong>2. AI analysis</strong>
            <span>Error analysis and feedback agents update grammar and vocabulary progression.</span>
          </div>
          <div className={styles.workflowItem}>
            <strong>3. Aggregation</strong>
            <span>XP, streaks, achievements, leaderboard, and notifications are recalculated live.</span>
          </div>
          <div className={styles.workflowItem}>
            <strong>4. Admin visibility</strong>
            <span>Dashboard charts, user management, logs, system status, and session control.</span>
          </div>
        </aside>
      </div>
    </div>
  );
};

export default AdminLogin;
