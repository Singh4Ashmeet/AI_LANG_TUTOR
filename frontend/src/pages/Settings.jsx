import React, { useState } from "react";
import { api } from "../api.js";
import styles from "./Settings.module.css";

const Settings = () => {
  const [theme, setTheme] = useState("dark");
  const [sounds, setSounds] = useState(true);
  const [immersion, setImmersion] = useState(false);
  const [dailyGoal, setDailyGoal] = useState(10);
  const [notificationTime, setNotificationTime] = useState("19:00");

  const save = async () => {
    await api.put("/users/me", {
      theme,
      sounds_enabled: sounds,
      immersion_mode: immersion,
      daily_goal_minutes: dailyGoal,
      notification_time: notificationTime
    });
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.eyebrow}>Settings</div>
        <h2>Personalize your experience</h2>
        <p>Tune goals, theme, and notifications.</p>
      </header>
      <div className={styles.card}>
        <div className={styles.row}>
          <label>Theme</label>
          <select value={theme} onChange={(event) => setTheme(event.target.value)}>
            <option value="dark">Dark</option>
            <option value="light">Light</option>
          </select>
        </div>
        <div className={styles.row}>
          <label>Sounds</label>
          <select value={sounds ? "on" : "off"} onChange={(event) => setSounds(event.target.value === "on")}>
            <option value="on">On</option>
            <option value="off">Off</option>
          </select>
        </div>
        <div className={styles.row}>
          <label>Immersion mode</label>
          <select value={immersion ? "on" : "off"} onChange={(event) => setImmersion(event.target.value === "on")}>
            <option value="off">Off</option>
            <option value="on">On</option>
          </select>
        </div>
        <div className={styles.row}>
          <label>Daily goal</label>
          <div className={styles.goalButtons}>
            {[5, 10, 20, 30].map((value) => (
              <button
                key={value}
                type="button"
                className={dailyGoal === value ? styles.active : ""}
                onClick={() => setDailyGoal(value)}
              >
                {value} min
              </button>
            ))}
          </div>
        </div>
        <div className={styles.row}>
          <label>Reminder time</label>
          <input type="time" value={notificationTime} onChange={(event) => setNotificationTime(event.target.value)} />
        </div>
        <button type="button" className={styles.primary} onClick={save}>
          Save settings
        </button>
      </div>
    </div>
  );
};

export default Settings;

