import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";
import styles from "./JournalNew.module.css";

const JournalNew = () => {
  const navigate = useNavigate();
  const [entry, setEntry] = useState("");
  const [topic] = useState("Write about your last trip.");

  const submit = async () => {
    await api.post("/journal", { text: entry, topic });
    navigate("/practice/journal");
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.eyebrow}>Journal entry</div>
        <h2>{topic}</h2>
        <p>Write 100-300 words in your target language.</p>
      </header>
      <textarea value={entry} onChange={(event) => setEntry(event.target.value)} />
      <button type="button" onClick={submit} disabled={entry.length < 20}>
        Submit journal
      </button>
    </div>
  );
};

export default JournalNew;

