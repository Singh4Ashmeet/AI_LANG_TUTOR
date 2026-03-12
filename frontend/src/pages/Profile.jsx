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

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div className={styles.avatar} style={{ background: user?.avatar_color || "#58CC02" }}>
          {user?.username?.[0]?.toUpperCase()}
        </div>
        <div>
          <h2>{user?.username}</h2>
          <p>
            {user?.cefr_level || "A1"} · {user?.native_language || "Native"} → {user?.target_language || "Target"}
          </p>
        </div>
      </div>

      <div className={styles.statsGrid}>
        <div className={styles.statCard}>XP: {stats?.xp ?? 0}</div>
        <div className={styles.statCard}>Streak: {stats?.streak ?? 0}</div>
        <div className={styles.statCard}>Words: {stats?.vocabulary?.learning ?? 0}</div>
        <div className={styles.statCard}>Lessons: {stats?.total_sessions ?? 0}</div>
      </div>

      <div className={styles.links}>
        <Link to="/profile/achievements">Achievements</Link>
        <Link to="/settings">Settings</Link>
      </div>
    </div>
  );
};

export default Profile;

