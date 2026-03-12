import React, { useEffect, useState } from "react";
import { api } from "../../api.js";
import styles from "./AdminLeaderboard.module.css";

const AdminLeaderboard = () => {
  const [entries, setEntries] = useState([]);

  useEffect(() => {
    api.get("/admin/leaderboard").then((data) => setEntries(data.items || []));
  }, []);

  const remove = async (userId) => {
    await api.delete(`/admin/leaderboard/${userId}`);
    const data = await api.get("/admin/leaderboard");
    setEntries(data.items || []);
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h2>Leaderboard</h2>
        <p>Weekly rankings and anti-cheat tools.</p>
      </header>
      <div className={styles.table}>
        <div className={styles.tableHeader}>
          <span>Rank</span>
          <span>User</span>
          <span>Weekly XP</span>
          <span>Week start</span>
          <span>Action</span>
        </div>
        {entries.map((entry, index) => (
          <div key={entry._id} className={styles.tableRow}>
            <span>{entry.rank ?? index + 1}</span>
            <span>{entry.username}</span>
            <span>{entry.weekly_xp}</span>
            <span>{entry.week_start ? new Date(entry.week_start).toLocaleDateString() : "—"}</span>
            <button type="button" className={styles.danger} onClick={() => remove(entry.user_id)}>
              Remove
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AdminLeaderboard;

