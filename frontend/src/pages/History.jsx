import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import styles from "./History.module.css";

const History = () => {
  const [sessions, setSessions] = useState([]);

  useEffect(() => {
    api.get("/history").then((data) => setSessions(data.items || []));
  }, []);

  const totalXp = sessions.reduce((sum, session) => sum + (session.xp_earned || 0), 0);
  const avgAccuracy = sessions.length
    ? Math.round(sessions.reduce((sum, session) => sum + (session.accuracy_percent || 0), 0) / sessions.length)
    : 0;

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.eyebrow}>History</div>
        <h2>Session history</h2>
        <p>Review past lessons and conversations.</p>
      </header>
      <section className={styles.summary}>
        <article className={styles.summaryCard}>
          <span>Sessions</span>
          <strong>{sessions.length}</strong>
        </article>
        <article className={styles.summaryCard}>
          <span>XP logged</span>
          <strong>{totalXp}</strong>
        </article>
        <article className={styles.summaryCard}>
          <span>Avg accuracy</span>
          <strong>{avgAccuracy}%</strong>
        </article>
      </section>
      <div className={styles.list}>
        {sessions.map((session) => (
          <Link key={session._id} to={`/history/${session._id}`} className={styles.card}>
            <div className={styles.cardMain}>
              <strong>{session.session_type}</strong>
              <span>{session.scenario || session.skill_id || "Practice session"}</span>
            </div>
            <div className={styles.cardStats}>
              <span>{session.xp_earned || 0} XP</span>
              <span>{session.accuracy_percent || 0}% accuracy</span>
              <span>{Math.round((session.duration_seconds || 0) / 60)} min</span>
            </div>
            <div className={styles.meta}>{new Date(session.started_at).toLocaleString()}</div>
          </Link>
        ))}
      </div>
    </div>
  );
};

export default History;
