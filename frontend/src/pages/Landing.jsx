import React from "react";
import { Link } from "react-router-dom";
import styles from "./Landing.module.css";

const Landing = () => (
  <div className={styles.page}>
    <header className={styles.hero}>
      <div className={styles.heroText}>
        <div className={styles.eyebrow}>LinguAI</div>
        <h1>Master languages with an AI-powered path that feels alive.</h1>
        <p>
          Lessons, roleplay, pronunciation, journaling, and progress coaching designed to move like a real learning
          companion instead of a static course.
        </p>
        <div className={styles.actions}>
          <Link to="/register" className={styles.primary}>
            Get started
          </Link>
          <Link to="/login" className={styles.secondary}>
            Sign in
          </Link>
          <Link to="/admin/login" className={styles.secondary}>
            Admin portal
          </Link>
        </div>
        <div className={styles.signalRow}>
          <div><strong>Live AI tutor</strong><span>Explain, practice, and roleplay on demand.</span></div>
          <div><strong>Secure login</strong><span>OTP plus single-device sessions keep accounts safe.</span></div>
        </div>
      </div>
      <div className={styles.heroCard}>
        <div className={styles.heroLabel}>Learning cockpit</div>
        <div className={styles.heroStat}>
          <strong>40-60 skills</strong>
          <span>per language path</span>
        </div>
        <div className={styles.heroStat}>
          <strong>10 exercise types</strong>
          <span>with AI-backed corrections</span>
        </div>
        <div className={styles.heroStat}>
          <strong>Stories, voice, journal</strong>
          <span>practice beyond basic lessons</span>
        </div>
        <div className={styles.heroPanel}>
          <div><span>Path</span><strong>Adaptive</strong></div>
          <div><span>Feedback</span><strong>Instant</strong></div>
          <div><span>Motivation</span><strong>Streak + XP</strong></div>
        </div>
      </div>
    </header>
    <section className={styles.features}>
      {[
        { title: "Path map", text: "Winding skill tree with unlockable crowns and chests." },
        { title: "AI tutor", text: "Explain, practice, and roleplay modes for every level." },
        { title: "Pronunciation studio", text: "Record and compare with guided feedback." },
        { title: "Immersion mode", text: "Switch the whole UI into your target language." },
        { title: "Journal and grammar", text: "Write daily and drill specific rules you keep missing." },
        { title: "Social pressure, but fun", text: "Friends, challenges, and leaderboards turn consistency into a game." }
      ].map((feature) => (
        <div key={feature.title} className={styles.featureCard}>
          <h3>{feature.title}</h3>
          <p>{feature.text}</p>
        </div>
      ))}
    </section>
  </div>
);

export default Landing;
