import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import styles from "./OtpVerify.module.css";

const DEVELOPMENT_OTP_CODE = "000000";

const OtpVerify = () => {
  const navigate = useNavigate();
  const { verifyOtp, resendOtp } = useAuth();
  const [digits, setDigits] = useState(Array(6).fill(""));
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);
  const [deliveryMode, setDeliveryMode] = useState(() => localStorage.getItem("otp_delivery_mode") || "email");
  const inputRefs = useRef([]);

  useEffect(() => {
    inputRefs.current[0]?.focus();
  }, []);

  useEffect(() => {
    if (resendCooldown <= 0) return undefined;
    const timer = setInterval(() => {
      setResendCooldown((seconds) => (seconds > 0 ? seconds - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, [resendCooldown]);

  const moveFocus = (index) => {
    const target = inputRefs.current[index];
    if (target) target.focus();
  };

  const handleChange = (index, rawValue) => {
    const value = rawValue.replace(/\D/g, "");
    if (!value) {
      const next = [...digits];
      next[index] = "";
      setDigits(next);
      return;
    }

    const next = [...digits];
    next[index] = value.slice(-1);
    setDigits(next);
    if (index < 5) moveFocus(index + 1);
  };

  const handleKeyDown = (index, event) => {
    if (event.key === "Backspace" && !digits[index] && index > 0) {
      moveFocus(index - 1);
    }
    if (event.key === "ArrowLeft" && index > 0) {
      event.preventDefault();
      moveFocus(index - 1);
    }
    if (event.key === "ArrowRight" && index < 5) {
      event.preventDefault();
      moveFocus(index + 1);
    }
  };

  const handlePaste = (event) => {
    event.preventDefault();
    const value = event.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
    if (!value) return;
    const next = Array(6).fill("");
    value.split("").forEach((char, idx) => {
      next[idx] = char;
    });
    setDigits(next);
    moveFocus(Math.min(value.length, 5));
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
    setNotice("");
    try {
      const result = await verifyOtp(code);
      if (result.totpRequired) {
        navigate("/login/totp");
      } else if (result.user?.role === "admin") {
        navigate("/admin");
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
    if (resendCooldown > 0) return;
    setError("");
    setNotice("");
    try {
      const result = await resendOtp();
      setDeliveryMode(result?.delivery_mode || "email");
      setResendCooldown(30);
      setNotice(
        (result?.delivery_mode || "email") === "development_bypass"
          ? "Development OTP refreshed."
          : "A fresh OTP was sent. Please check your inbox."
      );
      setDigits(Array(6).fill(""));
      moveFocus(0);
    } catch (err) {
      setError(err.message || "Unable to resend OTP.");
    }
  };

  const enteredDigits = digits.filter(Boolean).length;
  const progressPercent = Math.round((enteredDigits / 6) * 100);

  return (
    <div className={styles.page}>
      <div className={styles.glowA} />
      <div className={styles.glowB} />
      <div className={styles.card}>
        <h2>Enter your verification code</h2>
        <p>
          {deliveryMode === "development_bypass"
            ? "Local development fallback is active. Paste works too."
            : "We sent a 6-digit code to your email. Paste works too."}
        </p>
        {deliveryMode === "development_bypass" && (
          <div className={styles.devBanner}>
            Gmail OTP delivery is unavailable locally, so development mode is using code <strong>{DEVELOPMENT_OTP_CODE}</strong>.
          </div>
        )}
        <div className={styles.progressWrap}>
          <div className={styles.progressTrack}>
            <div className={styles.progressFill} style={{ width: `${progressPercent}%` }} />
          </div>
          <span>{enteredDigits}/6 digits</span>
        </div>
        {error && <div className={styles.error}>{error}</div>}
        {notice && <div className={styles.notice}>{notice}</div>}
        <form onSubmit={submit} className={styles.form}>
          <div className={styles.codeRow} onPaste={handlePaste}>
            {digits.map((digit, index) => (
              <input
                key={index}
                ref={(el) => {
                  inputRefs.current[index] = el;
                }}
                value={digit}
                onChange={(event) => handleChange(index, event.target.value)}
                onKeyDown={(event) => handleKeyDown(index, event)}
                inputMode="numeric"
                maxLength={1}
                autoComplete="one-time-code"
              />
            ))}
          </div>
          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Verifying..." : "Verify"}
          </button>
        </form>
        <button type="button" className={styles.link} onClick={resend} disabled={resendCooldown > 0}>
          {resendCooldown > 0 ? `Resend in ${resendCooldown}s` : "Resend code"}
        </button>
      </div>
    </div>
  );
};

export default OtpVerify;
