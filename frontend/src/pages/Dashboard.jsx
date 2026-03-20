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
  const vocabTotal = Object.values(stats?.vocabulary || {}).reduce((sum, value) => sum + value, 0);
  const quickStats = [
    { label: "Weekly XP", value: stats?.weekly_xp ?? user?.weekly_xp ?? 0, tone: "blue" },
    { label: "Words tracked", value: vocabTotal, tone: "gold" },
    { label: "Lessons finished", value: stats?.total_lessons_complete ?? 0, tone: "green" },
    { label: "Achievements", value: stats?.achievements_earned ?? 0, tone: "violet" }
  ];
  const practiceModes = [
    { title: "Flashcards", text: "Recover weak vocabulary with spaced repetition.", to: "/practice/flashcards" },
    { title: "Roleplay", text: "Jump into real-life conversations with AI characters.", to: "/roleplay" },
    { title: "Journal", text: "Write a short entry and get feedback on fluency.", to: "/practice/journal" }
  ];

  return (
    <div className={styles.page}>
      <div className={styles.hero}>
        <div className={styles.heroCopy}>
          <div className={styles.eyebrow}>Today's focus</div>
          <h1>Welcome back, {user?.username}</h1>
          <p>
            Your path is already moving. Keep the streak alive, hit your goal ring, and use practice modes that match
            where you are right now.
          </p>
          <div className={styles.heroActions}>
            <Link to="/practice/flashcards" className={styles.primaryAction}>
              Start review
            </Link>
            <Link to="/practice" className={styles.secondaryAction}>
              Open practice hub
            </Link>
          </div>
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

      <section className={styles.quickGrid}>
        {quickStats.map((item) => (
          <article key={item.label} className={`${styles.quickCard} ${styles[item.tone]}`}>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </article>
        ))}
      </section>

      <section className={styles.spotlightGrid}>
        <article className={styles.spotlightCard}>
          <div className={styles.cardEyebrow}>Momentum</div>
          <h3>Your learner snapshot</h3>
          <div className={styles.snapshotList}>
            <div>
              <strong>{stats?.xp ?? user?.xp ?? 0}</strong>
              <span>Total XP in current level track</span>
            </div>
            <div>
              <strong>{stats?.total_minutes_practiced ?? 0}m</strong>
              <span>Total minutes practiced</span>
            </div>
            <div>
              <strong>{stats?.streak_freeze ?? user?.streak_freeze ?? 0}</strong>
              <span>Streak freezes available</span>
            </div>
          </div>
        </article>

        <article className={styles.spotlightCard}>
          <div className={styles.cardEyebrow}>Recommended next</div>
          <h3>Keep the engine warm</h3>
          <div className={styles.recommendList}>
            {practiceModes.map((mode) => (
              <Link key={mode.title} to={mode.to} className={styles.recommendItem}>
                <div>
                  <strong>{mode.title}</strong>
                  <span>{mode.text}</span>
                </div>
                <em>Open</em>
              </Link>
            ))}
          </div>
        </article>
      </section>

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
            <div className={styles.wordMeta}>
              <span>{word?.part_of_speech}</span>
              <span>{word?.example_translation}</span>
            </div>
          </div>
        )}
      </section>

      <section className={styles.pathSection}>
        <div className={styles.sectionHeader}>
          <h2>Learning path</h2>
          <p>Follow the winding path and unlock each skill.</p>
        </div>
        {curriculum?.sections ? <PathMap sections={curriculum.sections} user={user} /> : <div className={styles.loading}>Loading curriculum...</div>}
      </section>

      <Link className={styles.fab} to="/practice/flashcards">
        Practice
      </Link>
    </div>
  );
};

export default Dashboard;
