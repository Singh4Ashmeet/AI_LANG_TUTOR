import React, { useEffect, useState } from "react";
import { api } from "../../api.js";
import styles from "./AdminSystem.module.css";

const AdminSystem = () => {
  const [setupData, setSetupData] = useState(null);
  const [code, setCode] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [envStatus, setEnvStatus] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [llmTest, setLlmTest] = useState("");

  const load = async () => {
    const env = await api.get("/admin/system/status");
    setEnvStatus(env.env);
    const live = await api.get("/admin/system/sessions");
    setSessions(live.items || []);
  };

  useEffect(() => {
    load();
  }, []);

  const startSetup = async () => {
    setError("");
    setStatus("");
    const data = await api.get("/admin/system/totp/setup");
    if (data.enabled) {
      setStatus("TOTP is already enabled.");
      return;
    }
    setSetupData(data);
  };

  const confirmSetup = async () => {
    setError("");
    setStatus("");
    try {
      await api.post("/admin/system/totp/confirm", { code });
      setStatus("TOTP enabled successfully.");
      setSetupData(null);
      setCode("");
    } catch (err) {
      setError(err.message);
    }
  };

  const testLlm = async () => {
    const data = await api.post("/admin/system/test-llm");
    setLlmTest(String(data.response || ""));
  };

  const testOtp = async () => {
    await api.post("/admin/system/test-otp");
    setStatus("Test OTP email sent.");
  };

  const seedWord = async () => {
    await api.post("/admin/word-of-day/seed");
    setStatus("Word of the Day seeded.");
  };

  const killAll = async () => {
    await api.delete("/admin/system/sessions/all");
    await load();
  };

  const qrUrl = setupData?.otpauth_url
    ? `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(setupData.otpauth_url)}`
    : null;

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h2>System</h2>
        <p>Check infrastructure and automation health.</p>
      </header>

      <section className={styles.panel}>
        <h3>Environment</h3>
        <div className={styles.envGrid}>
          {envStatus &&
            Object.entries(envStatus).map(([key, ok]) => (
              <div key={key} className={styles.envRow}>
                <span>{key}</span>
                <span className={ok ? styles.ok : styles.missing}>{ok ? "✓" : "✗"}</span>
              </div>
            ))}
        </div>
      </section>

      <section className={styles.panel}>
        <h3>Providers</h3>
        <div className={styles.actions}>
          <button type="button" onClick={testLlm}>
            Test LLM
          </button>
          <button type="button" className={styles.secondary} onClick={testOtp}>
            Send test OTP
          </button>
          <button type="button" className={styles.secondary} onClick={seedWord}>
            Seed Word of Day
          </button>
        </div>
        {llmTest && <div className={styles.helper}>LLM response: {llmTest}</div>}
        {status && <div className={styles.helper}>{status}</div>}
        {error && <div className={styles.error}>{error}</div>}
      </section>

      <section className={styles.panel}>
        <h3>Admin TOTP</h3>
        <button className={styles.primary} type="button" onClick={startSetup}>
          Set up admin TOTP
        </button>
        {setupData && (
          <div className={styles.totp}>
            {qrUrl && <img src={qrUrl} alt="TOTP QR code" />}
            <div className={styles.helper}>Secret: {setupData.secret}</div>
            <div className={styles.formRow}>
              <input
                type="text"
                inputMode="numeric"
                placeholder="Authenticator code"
                value={code}
                onChange={(event) => setCode(event.target.value)}
              />
              <button type="button" onClick={confirmSetup}>
                Confirm
              </button>
            </div>
          </div>
        )}
      </section>

      <section className={styles.panel}>
        <div className={styles.sessionsHeader}>
          <h3>Active sessions</h3>
          <button className={styles.danger} type="button" onClick={killAll}>
            Kill all sessions
          </button>
        </div>
        <div className={styles.table}>
          <div className={styles.tableHeader}>
            <span>User</span>
            <span>Device</span>
            <span>IP</span>
            <span>Last active</span>
          </div>
          {sessions.map((session) => (
            <div key={session._id} className={styles.tableRow}>
              <span className={styles.username}>{session.username || session.user_id}</span>
              <span>{session.device_info || "—"}</span>
              <span>{session.ip_address || "—"}</span>
              <span>{session.last_active ? new Date(session.last_active).toLocaleString() : "—"}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
};

export default AdminSystem;

