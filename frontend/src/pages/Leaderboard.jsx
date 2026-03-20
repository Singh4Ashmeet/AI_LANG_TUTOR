import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import { useAuth } from "../context/AuthContext.jsx";
import styles from "./Leaderboard.module.css";

const Leaderboard = () => {
  const { user } = useAuth();
  const [weekly, setWeekly] = useState([]);
  const [friends, setFriends] = useState([]);
  const [tab, setTab] = useState("weekly");

  useEffect(() => {
    api.get("/leaderboard/weekly").then((data) => setWeekly(data.items || []));
    api.get("/leaderboard/friends").then((data) => setFriends(data.items || []));
  }, []);

  const list = tab === "weekly" ? weekly : friends;
  const me = list.find((entry) => String(entry.user_id) === String(user?._id || user?.id) || entry.username === user?.username);
  const podium = list.slice(0, 3);
  const rest = list.slice(3);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.eyebrow}>League</div>
        <h2>Leaderboard</h2>
        <p>Compete with learners worldwide.</p>
      </header>
      <section className={styles.heroCard}>
        <div>
          <span className={styles.cardLabel}>Your standing</span>
          <strong>#{me?.rank || (me ? list.indexOf(me) + 1 : "--")}</strong>
        </div>
        <div>
          <span className={styles.cardLabel}>Weekly XP</span>
          <strong>{me?.weekly_xp ?? user?.weekly_xp ?? 0}</strong>
        </div>
        <div>
          <span className={styles.cardLabel}>View</span>
          <strong>{tab === "weekly" ? "Global" : "Friends"}</strong>
        </div>
      </section>
      <div className={styles.tabs}>
        <button type="button" className={tab === "weekly" ? styles.active : ""} onClick={() => setTab("weekly")}>
          Weekly
        </button>
        <button type="button" className={tab === "friends" ? styles.active : ""} onClick={() => setTab("friends")}>
          Friends
        </button>
      </div>
      <section className={styles.podium}>
        {podium.map((entry, index) => (
          <article key={entry._id || entry.user_id || index} className={styles.podiumCard}>
            <span className={styles.place}>#{entry.rank || index + 1}</span>
            <strong>{entry.username}</strong>
            <em>{entry.weekly_xp} XP</em>
          </article>
        ))}
      </section>
      <div className={styles.table}>
        <div className={styles.tableHeader}>
          <span>Rank</span>
          <span>User</span>
          <span>XP</span>
        </div>
        {rest.map((entry, index) => (
          <div key={entry._id || index} className={`${styles.tableRow} ${entry.username === user?.username ? styles.me : ""}`}>
            <span>{entry.rank || index + 4}</span>
            <span>{entry.username}</span>
            <span>{entry.weekly_xp}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Leaderboard;
