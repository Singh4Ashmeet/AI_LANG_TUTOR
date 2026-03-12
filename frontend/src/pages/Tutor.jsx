import React from "react";
import { Link } from "react-router-dom";
import styles from "./Tutor.module.css";

const Tutor = () => (
  <div className={styles.page}>
    <header className={styles.header}>
      <div className={styles.eyebrow}>AI Tutor</div>
      <h2>Choose a mode</h2>
      <p>Explain, practice, or roleplay with AI guidance.</p>
    </header>
    <div className={styles.grid}>
      <div className={styles.card}>
        <h3>Explain</h3>
        <p>Ask grammar questions and get clear answers.</p>
        <Link to="/tutor/chat">Start explain mode</Link>
      </div>
      <div className={styles.card}>
        <h3>Practice</h3>
        <p>Have a live conversation in your target language.</p>
        <Link to="/tutor/chat">Start practice</Link>
      </div>
      <div className={styles.card}>
        <h3>Roleplay</h3>
        <p>Jump into scenario-based conversations.</p>
        <Link to="/roleplay">Start roleplay</Link>
      </div>
    </div>
  </div>
);

export default Tutor;

