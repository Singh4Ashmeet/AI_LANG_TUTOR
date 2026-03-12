import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../context/AuthContext.jsx";
import PathMap from "../components/PathMap.jsx";
import styles from "./Dashboard.module.css";

const Dashboard = () => {
  const { user } = useAuth();
  const [stats, setStats] = useState({});
  const [curriculum, setCurriculum] = useState(null);
  const [word, setWord] = useState(null);
  const [wordOpen, setWordOpen] = useState(true);

  useEffect(() => {
    api.get("/users/me/stats").then(setStats).catch(() => {});
    api.get("/curriculum").then(setCurriculum).catch(() => {});
    api.get("/word-of-day").then(setWord).catch(() => {});
  }, []);

  const goalMinutes = user?.daily_goal_minutes || 10;
  const minutesDone = stats?.minutes_today || 0;
  const goalPercent = useMemo(
    () => Math.min(100, Math.round((minutesDone / goalMinutes) * 100)),
    [minutesDone, goalMinutes]
  );

  return (
    <div className={styles.page}>
      <div className={styles.hero}>
        <div>
          <div className={styles.eyebrow}>Today’s focus</div>
          <h1>Welcome back, {user?.username}</h1>
          <p>Stay on the path and keep the streak alive.</p>
        </div>
        <div className={styles.goalCard}>
          <div
            className={styles.goalRing}
            style={{ background: `conic-gradient(var(--accent) ${goalPercent}%, var(--soft) ${goalPercent}%)` }}
          >
            <div className={styles.goalCenter}>
              <span>{minutesDone}m</span>
              <small>of {goalMinutes}m</small>
            </div>
          </div>
          <div>
            <div className={styles.goalTitle}>Daily goal</div>
            <div className={styles.goalSub}>{goalPercent}% complete</div>
          </div>
        </div>
      </div>

      <section className={styles.wordSection}>
        <div className={styles.wordHeader}>
          <h2>Word of the day</h2>
          <button type="button" onClick={() => setWordOpen((prev) => !prev)}>
            {wordOpen ? "Collapse" : "Expand"}
          </button>
        </div>
        {wordOpen && (
          <div className={styles.wordCard}>
            <div className={styles.wordTitle}>{word?.word || "Loading..."}</div>
            <div className={styles.wordTranslation}>{word?.translation}</div>
            <div className={styles.wordExample}>{word?.example_sentence}</div>
            <div className={styles.wordMeta}>{word?.part_of_speech}</div>
          </div>
        )}
      </section>

      <section className={styles.pathSection}>
        <div className={styles.sectionHeader}>
          <h2>Learning path</h2>
          <p>Follow the winding path and unlock each skill.</p>
        </div>
        {curriculum?.sections ? (
          <PathMap sections={curriculum.sections} user={user} />
        ) : (
          <div className={styles.loading}>Loading curriculum...</div>
        )}
      </section>

      <Link className={styles.fab} to="/practice/flashcards">
        Practice
      </Link>
    </div>
  );
};

export default Dashboard;

