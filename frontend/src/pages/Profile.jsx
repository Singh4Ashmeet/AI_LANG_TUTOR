import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../context/AuthContext.jsx";
import styles from "./Profile.module.css";

const Profile = () => {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);

  useEffect(() => {
    api.get("/users/me/stats").then(setStats).catch(() => {});
  }, []);

  const metrics = [
    { label: "Weekly XP", value: stats?.weekly_xp ?? user?.weekly_xp ?? 0 },
    { label: "Total XP", value: stats?.total_xp ?? user?.total_xp ?? 0 },
    { label: "Words learned", value: stats?.total_words_learned ?? user?.total_words_learned ?? 0 },
    { label: "Minutes practiced", value: stats?.total_minutes_practiced ?? user?.total_minutes_practiced ?? 0 }
  ];

  return (
    <div className={styles.page}>
      <section className={styles.hero}>
        <div className={styles.identity}>
          <div className={styles.avatar} style={{ background: user?.avatar_color || "#58CC02" }}>
            {user?.username?.[0]?.toUpperCase()}
          </div>
          <div>
            <div className={styles.eyebrow}>Learner profile</div>
            <h2>{user?.username}</h2>
            <p>
              {user?.cefr_level || "A1"} learner | {user?.native_language || "Native"} to {user?.target_language || "Target"}
            </p>
            <div className={styles.badges}>
              <span>Streak {stats?.streak ?? user?.streak ?? 0}</span>
              <span>Gems {stats?.gems ?? user?.gems ?? 0}</span>
              <span>Hearts {stats?.hearts ?? user?.hearts ?? 0}</span>
            </div>
          </div>
        </div>
        <div className={styles.progressCard}>
          <span>Current momentum</span>
          <strong>{stats?.daily_goal_minutes ?? user?.daily_goal_minutes ?? 10} min daily goal</strong>
          <p>{stats?.achievements_earned ?? 0} achievements earned so far.</p>
        </div>
      </section>

      <section className={styles.statsGrid}>
        {metrics.map((metric) => (
          <article key={metric.label} className={styles.statCard}>
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
          </article>
        ))}
      </section>

      <section className={styles.panels}>
        <article className={styles.panel}>
          <h3>Vocabulary status</h3>
          <div className={styles.vocabGrid}>
            <div><strong>{stats?.vocabulary?.new ?? 0}</strong><span>New</span></div>
            <div><strong>{stats?.vocabulary?.learning ?? 0}</strong><span>Learning</span></div>
            <div><strong>{stats?.vocabulary?.known ?? 0}</strong><span>Known</span></div>
            <div><strong>{stats?.vocabulary?.mastered ?? 0}</strong><span>Mastered</span></div>
          </div>
        </article>

        <article className={styles.panel}>
          <h3>Session progress</h3>
          <div className={styles.timeline}>
            <div><strong>{stats?.xp ?? user?.xp ?? 0}</strong><span>Current XP</span></div>
            <div><strong>{stats?.total_sessions ?? 0}</strong><span>Total sessions</span></div>
            <div><strong>{stats?.total_lessons_complete ?? user?.total_lessons_complete ?? 0}</strong><span>Lessons complete</span></div>
          </div>
        </article>
      </section>

      <div className={styles.links}>
        <Link to="/profile/achievements">Open achievements</Link>
        <Link to="/settings">Adjust settings</Link>
        <Link to="/history">Review history</Link>
      </div>
    </div>
  );
};

export default Profile;
