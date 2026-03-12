import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import styles from "./SpeedRound.module.css";

const SpeedRound = () => {
  const [round, setRound] = useState(null);
  const [result, setResult] = useState(null);

  useEffect(() => {
    api.get("/bonus/speed-round/start").then(setRound);
  }, []);

  const finish = async () => {
    const data = await api.post("/bonus/speed-round/complete");
    setResult(data);
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.eyebrow}>Speed round</div>
        <h2>Match words fast</h2>
        <p>30 seconds to collect as many points as possible.</p>
      </header>
      <div className={styles.card}>
        <div>Round ID: {round?.round_id || "Loading..."}</div>
        <button type="button" onClick={finish}>
          Finish round
        </button>
        {result && <div className={styles.result}>XP: {result.xp}</div>}
      </div>
    </div>
  );
};

export default SpeedRound;

