import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import styles from "./Achievements.module.css";

const Achievements = () => {
  const [all, setAll] = useState([]);
  const [earned, setEarned] = useState([]);

  useEffect(() => {
    api.get("/achievements").then((data) => setAll(data.items || []));
    api.get("/achievements/earned").then((data) => setEarned(data.items || []));
  }, []);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.eyebrow}>Achievements</div>
        <h2>Achievement cabinet</h2>
        <p>Unlock badges as you progress.</p>
      </header>
      <div className={styles.grid}>
        {all.map((achievement) => {
          const unlocked = earned.includes(achievement.achievement_id);
          return (
            <div key={achievement.achievement_id} className={`${styles.card} ${!unlocked ? styles.locked : ""}`}>
              <div className={styles.icon}>{achievement.icon}</div>
              <h3>{achievement.title}</h3>
              <p>{achievement.description}</p>
              <span className={styles.badge}>{unlocked ? "Unlocked" : "Locked"}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default Achievements;

