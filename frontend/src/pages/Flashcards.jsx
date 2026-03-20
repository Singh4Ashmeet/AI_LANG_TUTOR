import React, { useEffect, useMemo, useState } from "react";
import { api } from "../api.js";
import styles from "./Flashcards.module.css";

const Flashcards = () => {
  const [cards, setCards] = useState([]);
  const [index, setIndex] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const [guess, setGuess] = useState("");
  const [sessionStats, setSessionStats] = useState({ reviewed: 0, streak: 0 });

  useEffect(() => {
    api.get("/flashcards").then((data) => setCards(data.cards || [])).catch(() => {});
  }, []);

  const current = cards[index];
  const progress = cards.length ? Math.round((index / cards.length) * 100) : 0;

  const guessScore = useMemo(() => {
    if (!revealed || !current) return null;
    const expected = (current.translation || "").trim().toLowerCase();
    const actual = guess.trim().toLowerCase();
    if (!actual) return "no_guess";
    if (actual === expected) return "strong";
    if (expected.includes(actual) || actual.includes(expected)) return "close";
    return "retry";
  }, [revealed, current, guess]);

  const revealCard = () => {
    setRevealed(true);
  };

  const review = async (quality) => {
    if (!current) return;
    await api.post("/flashcards/review", { card_id: current._id, quality });
    setSessionStats((prev) => ({
      reviewed: prev.reviewed + 1,
      streak: quality >= 4 ? prev.streak + 1 : 0
    }));
    setRevealed(false);
    setGuess("");
    setIndex((prev) => prev + 1);
  };

  if (!current) {
    return (
      <div className={styles.emptyState}>
        <div className={styles.emptyCard}>
          <div className={styles.eyebrow}>Review complete</div>
          <h2>No cards due right now</h2>
          <p>Your spaced repetition queue is clear. Come back later or learn new words in lessons and stories.</p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <div className={styles.eyebrow}>Daily review</div>
          <h2>Recall before reveal</h2>
          <p>Try to remember the meaning first, then flip the card and rate how hard it felt.</p>
        </div>
        <div className={styles.summary}>
          <div>
            <strong>{sessionStats.reviewed}</strong>
            <span>Reviewed</span>
          </div>
          <div>
            <strong>{sessionStats.streak}</strong>
            <span>Strong streak</span>
          </div>
          <div>
            <strong>{cards.length - index}</strong>
            <span>Left</span>
          </div>
        </div>
      </header>

      <div className={styles.progressShell}>
        <div className={styles.progressFill} style={{ width: `${progress}%` }} />
      </div>

      <div className={styles.layout}>
        <section className={styles.cardPanel}>
          <div className={styles.promptCard}>
            <div className={styles.promptEyebrow}>Target word</div>
            <div className={styles.front}>{current.word}</div>
            {current.context_sentence && <div className={styles.contextHint}>{current.context_sentence}</div>}
          </div>

          {!revealed ? (
            <div className={styles.recallPanel}>
              <label className={styles.inputLabel} htmlFor="flashcard-guess">
                Type the meaning before you flip
              </label>
              <input
                id="flashcard-guess"
                value={guess}
                onChange={(event) => setGuess(event.target.value)}
                placeholder="Your best guess"
              />
              <button type="button" className={styles.primary} onClick={revealCard}>
                Reveal answer
              </button>
            </div>
          ) : (
            <div className={styles.answerPanel}>
              <div className={styles.answerHeader}>
                <span>Answer</span>
                {guessScore === "strong" && <strong className={styles.strong}>Great recall</strong>}
                {guessScore === "close" && <strong className={styles.close}>Close enough</strong>}
                {guessScore === "retry" && <strong className={styles.retry}>Good review moment</strong>}
              </div>
              <div className={styles.translation}>{current.translation || "No translation saved yet"}</div>
              {guess && <div className={styles.guess}>Your guess: {guess}</div>}
              {current.context_sentence && <div className={styles.context}>{current.context_sentence}</div>}
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
            </div>
          )}
        </section>

        <aside className={styles.sidebar}>
          <div className={styles.sidebarCard}>
            <span>Why this works</span>
            <p>Strong memory practice happens when you try to recall before seeing the answer. That makes review feel much closer to Duolingo’s active learning style.</p>
          </div>
          <div className={styles.sidebarCard}>
            <span>How to rate</span>
            <p>`Again` if you blanked, `Hard` if you hesitated, `Good` if it came back with effort, and `Easy` if it felt instant.</p>
          </div>
        </aside>
      </div>
    </div>
  );
};

export default Flashcards;
