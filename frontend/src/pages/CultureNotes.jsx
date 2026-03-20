import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import styles from "./CultureNotes.module.css";

const CultureNotes = () => {
  const [note, setNote] = useState(null);
  const [xp, setXp] = useState(null);

  useEffect(() => {
    api.get("/bonus/culture-notes").then(setNote).catch(() => {});
  }, []);

  const markRead = async () => {
    if (!note) return;
    const data = await api.post(`/bonus/culture-notes/${note.id}/read`, { accepted: true });
    setXp(data.xp);
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.eyebrow}>Culture Notes</div>
        <h2>{note?.title || "Cultural insight"}</h2>
        <p>Learn context beyond vocabulary and grammar.</p>
      </header>
      <div className={styles.note}>
        {(note?.paragraphs || []).map((paragraph, index) => (
          <p key={index}>{paragraph}</p>
        ))}
      </div>
      <button type="button" className={styles.button} onClick={markRead}>
        Mark as read
      </button>
      {xp !== null && <div className={styles.reward}>XP +{xp}</div>}
    </div>
  );
};

export default CultureNotes;
