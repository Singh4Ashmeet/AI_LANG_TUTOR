import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import styles from "./OtpVerify.module.css";

const OtpVerify = () => {
  const navigate = useNavigate();
  const { verifyOtp, resendOtp } = useAuth();
  const [digits, setDigits] = useState(Array(6).fill(""));
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleChange = (index, value) => {
    const next = [...digits];
    next[index] = value.slice(-1);
    setDigits(next);
  };

  const submit = async (event) => {
    event.preventDefault();
    const code = digits.join("");
    if (code.length !== 6) {
      setError("Enter the 6-digit code.");
      return;
    }
    setIsSubmitting(true);
    setError("");
    try {
      const result = await verifyOtp(code);
      if (result.totpRequired) {
        navigate("/login/totp");
      } else if (!result.user?.onboarding_complete) {
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

  const resend = async () => {
    try {
      await resendOtp();
    } catch (err) {
      setError(err.message || "Unable to resend OTP.");
    }
  };

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <h2>Enter your verification code</h2>
        <p>We sent a 6-digit code to your email.</p>
        {error && <div className={styles.error}>{error}</div>}
        <form onSubmit={submit} className={styles.form}>
          <div className={styles.codeRow}>
            {digits.map((digit, index) => (
              <input
                key={index}
                value={digit}
                onChange={(event) => handleChange(index, event.target.value)}
                inputMode="numeric"
                maxLength={1}
              />
            ))}
          </div>
          <button type="submit" disabled={isSubmitting}>
            Verify
          </button>
        </form>
        <button type="button" className={styles.link} onClick={resend}>
          Resend code
        </button>
      </div>
    </div>
  );
};

export default OtpVerify;

