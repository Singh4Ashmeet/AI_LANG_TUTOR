import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import styles from "./Reading.module.css";

const Reading = () => {
  const [item, setItem] = useState(null);
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/bonus/reading/start").then(setItem).catch((err) => setError(err.message));
  }, []);

  const setAnswer = (id, answer) => {
    setAnswers((prev) => ({ ...prev, [id]: answer }));
  };

  const submit = async () => {
    if (!item) return;
    const payload = {
      answers: Object.entries(answers).map(([id, answer]) => ({ id, answer })),
    };
    const data = await api.post(`/bonus/reading/${item.id}/submit`, payload);
    setResult(data);
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.eyebrow}>Reading Comprehension</div>
        <h2>{item?.title || "Reading challenge"}</h2>
        <p>Read first, then answer the questions.</p>
      </header>

      {error && <div className={styles.error}>{error}</div>}

      {item && (
        <>
          <article className={styles.article}>{item.article}</article>
          <div className={styles.questions}>
            {item.questions?.map((q) => (
              <div key={q.id} className={styles.card}>
                <h3>{q.question}</h3>
                <div className={styles.options}>
                  {q.options?.map((opt) => (
                    <button
                      key={opt}
                      type="button"
                      className={`${styles.option} ${answers[q.id] === opt ? styles.active : ""}`}
                      onClick={() => setAnswer(q.id, opt)}
                    >
                      {opt}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
          <button type="button" className={styles.submit} onClick={submit}>
            Submit
          </button>
        </>
      )}

      {result && (
        <div className={styles.result}>
          Score: {result.score}/{result.total} • XP +{result.xp}
        </div>
      )}
    </div>
  );
};

export default Reading;
