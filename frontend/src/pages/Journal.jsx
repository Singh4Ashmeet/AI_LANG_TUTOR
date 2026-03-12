import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import styles from "./Journal.module.css";

const Journal = () => {
  const [entries, setEntries] = useState([]);

  useEffect(() => {
    api.get("/journal").then((data) => setEntries(data.items || []));
  }, []);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.eyebrow}>Journal</div>
        <h2>Daily writing</h2>
        <p>Write 100-300 words and get feedback.</p>
      </header>
      <Link to="/practice/journal/new" className={styles.primary}>
        Write a new entry
      </Link>
      <div className={styles.list}>
        {entries.map((entry) => (
          <div key={entry._id} className={styles.card}>
            <h3>{entry.topic || "Journal entry"}</h3>
            <p>{entry.created_at ? new Date(entry.created_at).toLocaleDateString() : "—"}</p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Journal;

