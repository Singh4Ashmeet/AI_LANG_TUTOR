import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../context/AuthContext.jsx";
import styles from "./Practice.module.css";

const Practice = () => {
  const { user } = useAuth();
  const [stats, setStats] = useState({});

  useEffect(() => {
    api.get("/users/me/stats").then(setStats).catch(() => {});
  }, []);

  const featured = [
    { title: "Flashcards", text: "Review new words with spaced repetition.", to: "/practice/flashcards", accent: "green" },
    { title: "Stories", text: "Read stories with comprehension checks.", to: "/practice/stories", accent: "blue" },
    { title: "Listening", text: "Transcribe audio at native speed.", to: "/practice/listening", accent: "gold" }
  ];
  const weakGrammar = stats?.weak_grammar || [];
  const recentMistakes = stats?.recent_mistakes || [];
  const reviewHeadline = weakGrammar[0]?.rule
    ? `Practice ${weakGrammar[0].rule}`
    : "Build stronger spelling and recall";
  const labs = [
    { title: "Speed round", text: "Match words in 30 seconds.", to: "/practice/speed" },
    { title: "Vocab challenge", text: "Five quick questions every day.", to: "/practice/vocab-challenge" },
    { title: "Journal", text: "Daily writing with feedback.", to: "/practice/journal" },
    { title: "Grammar deep dive", text: "Structured grammar guide and practice.", to: "/grammar" },
    { title: "Pronunciation studio", text: "Record, compare, and improve.", to: "/pronunciation" },
    { title: "Reading challenge", text: "Longer passages with comprehension checks.", to: "/practice/reading" },
    { title: "Podcast mode", text: "Listen-like scripts and summarize key points.", to: "/practice/podcast" },
    { title: "Culture notes", text: "Context-rich insights linked to skill themes.", to: "/practice/culture-notes" }
  ];

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.eyebrow}>Practice hub</div>
        <h2>Sharpen what you learned today</h2>
        <p>
          {user?.username}, your strongest sessions come from mixing review, immersion, and production practice.
        </p>
      </header>

      <section className={styles.summaryRow}>
        <article className={styles.summaryCard}>
          <span>Minutes today</span>
          <strong>{stats?.minutes_today ?? 0}</strong>
          <p>Keep your daily ring moving with one focused activity.</p>
        </article>
        <article className={styles.summaryCard}>
          <span>Vocabulary in flow</span>
          <strong>{stats?.vocabulary?.learning ?? 0}</strong>
          <p>Words currently moving from recognition into active recall.</p>
        </article>
        <article className={styles.summaryCard}>
          <span>Target language</span>
          <strong>{(user?.target_language || "spanish").toUpperCase()}</strong>
          <p>Use immersion-heavy practice to build speed and confidence.</p>
        </article>
        <article className={styles.summaryCard}>
          <span>Review due</span>
          <strong>{stats?.vocabulary_due ?? 0}</strong>
          <p>Words ready for recall right now.</p>
        </article>
      </section>

      <section className={styles.personalizedPanel}>
        <div className={styles.personalizedHeader}>
          <div>
            <div className={styles.eyebrow}>Personalized practice</div>
            <h3>{reviewHeadline}</h3>
          </div>
          <Link to="/practice/flashcards" className={styles.personalizedLink}>
            Start review
          </Link>
        </div>
        <div className={styles.personalizedGrid}>
          <article className={styles.personalizedCard}>
            <span>Weak grammar</span>
            {weakGrammar.length ? (
              weakGrammar.map((item) => (
                <div key={item.rule} className={styles.personalizedItem}>
                  <strong>{item.rule}</strong>
                  <small>{item.errors} errors logged</small>
                </div>
              ))
            ) : (
              <p>No major weak grammar yet. Keep practicing to generate tailored drills.</p>
            )}
          </article>
          <article className={styles.personalizedCard}>
            <span>Recent trouble spots</span>
            {recentMistakes.length ? (
              recentMistakes.map((item, index) => (
                <div key={`${item.prompt}-${index}`} className={styles.personalizedItem}>
                  <strong>{item.rule || item.answer_mode || "Lesson review"}</strong>
                  <small>{item.prompt}</small>
                </div>
              ))
            ) : (
              <p>Your recent lessons are looking clean. New mistakes will appear here for focused review.</p>
            )}
          </article>
          <article className={styles.personalizedCard}>
            <span>Spelling and dictation</span>
            <div className={styles.personalizedItem}>
              <strong>Listen, type, and fix tiny slips</strong>
              <small>Lessons now accept close spellings more intelligently and surface hints when you miss by a little.</small>
            </div>
            <div className={styles.personalizedItem}>
              <strong>Why this matters</strong>
              <small>It gets you closer to Duolingo-style “almost there” feedback instead of flat right-or-wrong grading.</small>
            </div>
          </article>
        </div>
      </section>

      <section className={styles.featuredGrid}>
        {featured.map((item) => (
          <Link key={item.title} className={`${styles.featuredCard} ${styles[item.accent]}`} to={item.to}>
            <div className={styles.cardTag}>Recommended</div>
            <h3>{item.title}</h3>
            <p>{item.text}</p>
            <span>Open mode</span>
          </Link>
        ))}
      </section>

      <section className={styles.grid}>
        {labs.map((item) => (
          <Link className={styles.card} key={item.title} to={item.to}>
            <h3>{item.title}</h3>
            <p>{item.text}</p>
          </Link>
        ))}
      </section>
    </div>
  );
};

export default Practice;
