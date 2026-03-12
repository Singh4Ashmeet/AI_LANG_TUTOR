import React, { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import styles from "./LessonComplete.module.css";

const LessonComplete = () => {
  const { state } = useLocation();
  const earned = state?.earned ?? 0;
  const accuracy = state?.accuracy_percent ?? 0;
  const hearts = state?.hearts ?? 0;
  const [displayXp, setDisplayXp] = useState(0);

  useEffect(() => {
    let current = 0;
    const step = Math.max(1, Math.floor(earned / 20));
    const interval = setInterval(() => {
      current += step;
      if (current >= earned) {
        current = earned;
        clearInterval(interval);
      }
      setDisplayXp(current);
    }, 40);
    return () => clearInterval(interval);
  }, [earned]);

  const stars = accuracy === 100 ? 3 : accuracy >= 80 ? 2 : 1;

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <div className={styles.heading}>Well done!</div>
        <div className={styles.xp}>
          +{displayXp} XP
          <span>Total accuracy: {accuracy}%</span>
        </div>
        <div className={styles.stars}>
          {[1, 2, 3].map((index) => (
            <span key={index} className={index <= stars ? styles.starOn : styles.starOff}>
              ★
            </span>
          ))}
        </div>
        <div className={styles.hearts}>Hearts remaining: {hearts}</div>
        <div className={styles.tip}>Coach tip: Keep practicing the new phrases in short bursts.</div>
        <div className={styles.actions}>
          <Link to="/dashboard" className={styles.primary}>
            Back to path
          </Link>
          <Link to="/dashboard" className={styles.secondary}>
            Continue
          </Link>
        </div>
      </div>
    </div>
  );
};

export default LessonComplete;

