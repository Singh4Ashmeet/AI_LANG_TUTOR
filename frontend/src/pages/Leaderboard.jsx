import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import styles from "./Leaderboard.module.css";

const Leaderboard = () => {
  const [weekly, setWeekly] = useState([]);
  const [friends, setFriends] = useState([]);
  const [tab, setTab] = useState("weekly");

  useEffect(() => {
    api.get("/leaderboard/weekly").then((data) => setWeekly(data.items || []));
    api.get("/leaderboard/friends").then((data) => setFriends(data.items || []));
  }, []);

  const list = tab === "weekly" ? weekly : friends;

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.eyebrow}>League</div>
        <h2>Leaderboard</h2>
        <p>Compete with learners worldwide.</p>
      </header>
      <div className={styles.tabs}>
        <button type="button" className={tab === "weekly" ? styles.active : ""} onClick={() => setTab("weekly")}>
          Weekly
        </button>
        <button type="button" className={tab === "friends" ? styles.active : ""} onClick={() => setTab("friends")}>
          Friends
        </button>
      </div>
      <div className={styles.table}>
        <div className={styles.tableHeader}>
          <span>Rank</span>
          <span>User</span>
          <span>XP</span>
        </div>
        {list.map((entry, index) => (
          <div key={entry._id || index} className={styles.tableRow}>
            <span>{entry.rank || index + 1}</span>
            <span>{entry.username}</span>
            <span>{entry.weekly_xp}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Leaderboard;

