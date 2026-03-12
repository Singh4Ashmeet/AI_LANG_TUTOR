import React from "react";
import { Link } from "react-router-dom";
import styles from "./Landing.module.css";

const Landing = () => (
  <div className={styles.page}>
    <header className={styles.hero}>
      <div className={styles.heroText}>
        <div className={styles.eyebrow}>LinguAI</div>
        <h1>Master languages with an AI-powered learning path.</h1>
        <p>Lessons, roleplay, pronunciation, and smart progress tracking in one platform.</p>
        <div className={styles.actions}>
          <Link to="/register" className={styles.primary}>
            Get started
          </Link>
          <Link to="/login" className={styles.secondary}>
            Sign in
          </Link>
        </div>
      </div>
      <div className={styles.heroCard}>
        <div className={styles.heroStat}>
          <strong>40-60 skills</strong>
          <span>per language path</span>
        </div>
        <div className={styles.heroStat}>
          <strong>Multi-agent AI</strong>
          <span>personalized feedback</span>
        </div>
        <div className={styles.heroStat}>
          <strong>OTP security</strong>
          <span>single-device sessions</span>
        </div>
      </div>
    </header>
    <section className={styles.features}>
      {[
        { title: "Path map", text: "Winding skill tree with unlockable crowns and chests." },
        { title: "AI tutor", text: "Explain, practice, and roleplay modes for every level." },
        { title: "Pronunciation studio", text: "Record and compare with guided feedback." },
        { title: "Immersion mode", text: "Switch the whole UI into your target language." }
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

