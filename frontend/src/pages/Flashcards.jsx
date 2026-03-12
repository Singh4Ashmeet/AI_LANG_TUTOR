import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import styles from "./Flashcards.module.css";

const Flashcards = () => {
  const [cards, setCards] = useState([]);
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);

  useEffect(() => {
    api.get("/flashcards").then((data) => setCards(data.cards || []));
  }, []);

  const current = cards[index];

  const review = async (quality) => {
    await api.post("/flashcards/review", { card_id: current._id, quality });
    setFlipped(false);
    setIndex((prev) => prev + 1);
  };

  if (!current) {
    return <div className={styles.empty}>No cards due today.</div>;
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.eyebrow}>Daily review</div>
        <h2>Flashcards</h2>
        <p>Tap to flip and rate how it felt.</p>
      </header>
      <div className={styles.card} onClick={() => setFlipped((prev) => !prev)} role="button" tabIndex={0}>
        {flipped ? (
          <div className={styles.back}>
            <div className={styles.translation}>{current.translation}</div>
            <div className={styles.context}>{current.context_sentence}</div>
          </div>
        ) : (
          <div className={styles.front}>{current.word}</div>
        )}
      </div>
      {flipped && (
        <div className={styles.actions}>
          <button type="button" onClick={() => review(2)}>
            Again
          </button>
          <button type="button" onClick={() => review(3)}>
            Hard
          </button>
          <button type="button" onClick={() => review(4)}>
            Good
          </button>
          <button type="button" onClick={() => review(5)}>
            Easy
          </button>
        </div>
      )}
    </div>
  );
};

export default Flashcards;

