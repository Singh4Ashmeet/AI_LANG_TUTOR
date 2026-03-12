import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import styles from "./History.module.css";

const History = () => {
  const [sessions, setSessions] = useState([]);

  useEffect(() => {
    api.get("/history").then((data) => setSessions(data.items || []));
  }, []);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.eyebrow}>History</div>
        <h2>Session history</h2>
        <p>Review past lessons and conversations.</p>
      </header>
      <div className={styles.list}>
        {sessions.map((session) => (
          <Link key={session._id} to={`/history/${session._id}`} className={styles.card}>
            <div>{session.session_type}</div>
            <div className={styles.meta}>{new Date(session.started_at).toLocaleString()}</div>
          </Link>
        ))}
      </div>
    </div>
  );
};

export default History;

