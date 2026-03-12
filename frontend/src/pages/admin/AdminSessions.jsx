import React, { useEffect, useState } from "react";
import { api } from "../../api.js";
import styles from "./AdminSessions.module.css";

const AdminSessions = () => {
  const [sessions, setSessions] = useState([]);

  useEffect(() => {
    api.get("/admin/sessions?limit=100").then((data) => setSessions(data.items || []));
  }, []);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h2>Sessions</h2>
        <p>Review learning activity across the platform.</p>
      </header>
      <div className={styles.table}>
        <div className={styles.tableHeader}>
          <span>Type</span>
          <span>User</span>
          <span>Skill</span>
          <span>Accuracy</span>
          <span>XP</span>
          <span>Started</span>
        </div>
        {sessions.map((session) => (
          <div key={session._id} className={styles.tableRow}>
            <span>{session.session_type}</span>
            <span>{session.user_id}</span>
            <span>{session.skill_id || "—"}</span>
            <span>{session.accuracy_percent ?? "—"}</span>
            <span>{session.xp_earned ?? "—"}</span>
            <span>{session.started_at ? new Date(session.started_at).toLocaleString() : "—"}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AdminSessions;

