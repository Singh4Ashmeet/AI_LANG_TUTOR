import React from "react";
import { Link } from "react-router-dom";
import styles from "./Practice.module.css";

const Practice = () => (
  <div className={styles.page}>
    <header className={styles.header}>
      <div className={styles.eyebrow}>Practice hub</div>
      <h2>Choose a practice mode</h2>
      <p>Flashcards, stories, listening, and more.</p>
    </header>
    <div className={styles.grid}>
      <Link className={styles.card} to="/practice/flashcards">
        <h3>Flashcards</h3>
        <p>Review new words with spaced repetition.</p>
      </Link>
      <Link className={styles.card} to="/practice/stories">
        <h3>Stories</h3>
        <p>Read stories with comprehension checks.</p>
      </Link>
      <Link className={styles.card} to="/practice/listening">
        <h3>Listening</h3>
        <p>Transcribe audio at native speed.</p>
      </Link>
      <Link className={styles.card} to="/practice/speed">
        <h3>Speed round</h3>
        <p>Match words in 30 seconds.</p>
      </Link>
      <Link className={styles.card} to="/practice/vocab-challenge">
        <h3>Vocab challenge</h3>
        <p>Five quick questions every day.</p>
      </Link>
      <Link className={styles.card} to="/practice/journal">
        <h3>Journal</h3>
        <p>Daily writing with feedback.</p>
      </Link>
      <Link className={styles.card} to="/grammar">
        <h3>Grammar deep dive</h3>
        <p>Structured grammar guide and practice.</p>
      </Link>
      <Link className={styles.card} to="/pronunciation">
        <h3>Pronunciation studio</h3>
        <p>Record, compare, and improve.</p>
      </Link>
    </div>
  </div>
);

export default Practice;

