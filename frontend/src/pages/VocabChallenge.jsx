import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import styles from "./VocabChallenge.module.css";

const VocabChallenge = () => {
  const [challenge, setChallenge] = useState(null);
  const [result, setResult] = useState(null);

  useEffect(() => {
    api.get("/bonus/vocab-challenge/today").then(setChallenge);
  }, []);

  const submit = async () => {
    const data = await api.post("/bonus/vocab-challenge/submit", { answers: [] });
    setResult(data);
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.eyebrow}>Vocab challenge</div>
        <h2>Daily vocab challenge</h2>
        <p>Answer 5 quick questions in 60 seconds.</p>
      </header>
      <div className={styles.card}>
        <div>Challenge ID: {challenge?.challenge_id || "Loading..."}</div>
        <button type="button" onClick={submit}>
          Submit challenge
        </button>
        {result && <div className={styles.result}>XP: {result.xp}</div>}
      </div>
    </div>
  );
};

export default VocabChallenge;

