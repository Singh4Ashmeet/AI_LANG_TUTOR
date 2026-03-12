import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import styles from "./Listening.module.css";

const Listening = () => {
  const [challenge, setChallenge] = useState(null);
  const [answer, setAnswer] = useState("");
  const [result, setResult] = useState(null);

  useEffect(() => {
    api.get("/bonus/listening/1").then(setChallenge).catch(() => {});
  }, []);

  const submit = async () => {
    const data = await api.post(`/bonus/listening/${challenge?.id || "1"}/submit`, { answer });
    setResult(data);
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.eyebrow}>Listening</div>
        <h2>Listening challenge</h2>
        <p>Transcribe native-speed audio.</p>
      </header>
      <div className={styles.card}>
        <button type="button" className={styles.audio}>
          Play sample audio
        </button>
        <textarea
          value={answer}
          onChange={(event) => setAnswer(event.target.value)}
          placeholder="Type what you hear"
        />
        <button type="button" onClick={submit}>
          Submit
        </button>
        {result && <div className={styles.result}>XP earned: {result.xp}</div>}
      </div>
    </div>
  );
};

export default Listening;

