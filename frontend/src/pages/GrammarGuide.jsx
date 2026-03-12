import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import styles from "./GrammarGuide.module.css";

const GrammarGuide = () => {
  const [guide, setGuide] = useState(null);

  useEffect(() => {
    api.get("/grammar/guide").then(setGuide).catch(() => {});
  }, []);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.eyebrow}>Grammar deep dive</div>
        <h2>Grammar guide</h2>
        <p>Explore structured explanations and practice prompts.</p>
      </header>
      <div className={styles.card}>
        <pre className={styles.content}>{JSON.stringify(guide, null, 2)}</pre>
      </div>
    </div>
  );
};

export default GrammarGuide;

