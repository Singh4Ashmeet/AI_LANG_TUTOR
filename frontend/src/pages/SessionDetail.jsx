import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api.js";
import styles from "./SessionDetail.module.css";

const SessionDetail = () => {
  const { id } = useParams();
  const [session, setSession] = useState(null);

  useEffect(() => {
    api.get(`/history/${id}`).then(setSession);
  }, [id]);

  if (!session) {
    return <div className={styles.loading}>Loading session...</div>;
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h2>{session.session_type}</h2>
        <p>{new Date(session.started_at).toLocaleString()}</p>
      </header>
      <div className={styles.card}>
        {session.messages?.map((msg, idx) => (
          <div key={idx} className={styles.row}>
            <strong>{msg.role}</strong>
            <span>{msg.content}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default SessionDetail;

