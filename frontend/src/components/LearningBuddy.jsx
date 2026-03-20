import React from "react";
import styles from "./LearningBuddy.module.css";

const LearningBuddy = ({
  variant = "sprout",
  mood = "cheer",
  pose = "wave",
  size = "md",
  message,
  name,
  align = "left"
}) => (
  <div className={`${styles.wrapper} ${styles[size]} ${styles[align]}`}>
    {message && (
      <div className={`${styles.bubble} ${styles[align]}`}>
        {name && <span className={styles.name}>{name}</span>}
        <p>{message}</p>
      </div>
    )}
    <div className={`${styles.stage} ${styles[pose]}`}>
      <div className={styles.shadow} />
      <div className={`${styles.character} ${styles[variant]} ${styles[mood]}`}>
        <div className={styles.sparkA} />
        <div className={styles.sparkB} />
        <div className={styles.head}>
          <div className={`${styles.ear} ${styles.earLeft}`} />
          <div className={`${styles.ear} ${styles.earRight}`} />
          <div className={styles.face}>
            <span className={styles.eye} />
            <span className={styles.eye} />
            <span className={styles.mouth} />
          </div>
          <div className={styles.cheekLeft} />
          <div className={styles.cheekRight} />
        </div>
        <div className={styles.body}>
          <div className={`${styles.arm} ${styles.armLeft}`} />
          <div className={`${styles.arm} ${styles.armRight}`} />
          <div className={styles.belly} />
          <div className={`${styles.foot} ${styles.footLeft}`} />
          <div className={`${styles.foot} ${styles.footRight}`} />
        </div>
        <div className={styles.badge} />
      </div>
    </div>
  </div>
);

export default LearningBuddy;
