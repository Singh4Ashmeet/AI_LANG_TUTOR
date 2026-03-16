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

      {session.summary && (
        <div className={styles.summaryCard}>
          <h3>AI Coach Summary</h3>
          <p className={styles.summaryText}>{session.summary.summary}</p>
          
          {session.summary.key_vocabulary_used?.length > 0 && (
            <div className={styles.summarySection}>
              <h4>Key Vocabulary</h4>
              <div className={styles.tags}>
                {session.summary.key_vocabulary_used.map((word, i) => (
                  <span key={i} className={styles.tag}>{word}</span>
                ))}
              </div>
            </div>
          )}

          {session.summary.grammar_tips?.length > 0 && (
            <div className={styles.summarySection}>
              <h4>Grammar Tips</h4>
              <ul className={styles.tipList}>
                {session.summary.grammar_tips.map((tip, i) => (
                  <li key={i}>{tip}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

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

