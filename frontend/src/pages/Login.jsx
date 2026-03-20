import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import styles from "./Login.module.css";

const Login = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const otpDeliveryIssue = error.toLowerCase().includes("otp email");

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      await login(email, password);
      navigate("/login/otp");
    } catch (err) {
      setError(err.message || "Invalid email or password.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className={styles.page}>
      <div className={styles.glowA} />
      <div className={styles.glowB} />
      <div className={styles.layout}>
        <section className={styles.story}>
          <span className={styles.kicker}>LinguAI</span>
          <h1>Practice like a real conversation, not a worksheet.</h1>
          <p>
            Your tutor, streak, and progress all continue right after OTP verification. Keep momentum and jump
            straight into the next lesson.
          </p>
          <div className={styles.stats}>
            <article className={styles.statCard}>
              <strong>10 exercise modes</strong>
              <span>From listening to roleplay with instant corrections.</span>
            </article>
            <article className={styles.statCard}>
              <strong>Single-device session lock</strong>
              <span>Your account stays secure if another login is detected.</span>
            </article>
            <article className={styles.statCard}>
              <strong>Adaptive AI coach</strong>
              <span>Feedback personalized to your CEFR level and weak spots.</span>
            </article>
          </div>
        </section>

        <div className={styles.card}>
          <div className={styles.header}>
            <h2>Welcome back</h2>
            <p>Log in to continue your learning path.</p>
          </div>
          {error && <div className={styles.error}>{error}</div>}
          {otpDeliveryIssue && (
            <div className={styles.hint}>
              OTP delivery is down right now. If you are running locally, check your Gmail App Password configuration.
            </div>
          )}
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
                  <span>{showPassword ? "Mask" : "Peek"}</span>
                </button>
              </div>
            </label>
            <button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Sending OTP..." : "Continue"}
            </button>
          </form>
          <div className={styles.links}>
            <Link to="/forgot-password">Forgot password?</Link>
            <Link to="/register">Create account</Link>
          </div>
          <div className={styles.adminLink}>
            <Link to="/admin/login">Open admin login</Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
