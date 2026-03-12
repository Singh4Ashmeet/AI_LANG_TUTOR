import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import styles from "./Challenges.module.css";

const Challenges = () => {
  const [challenges, setChallenges] = useState([]);
  const [targetId, setTargetId] = useState("");

  useEffect(() => {
    api.get("/users/challenges").then((data) => setChallenges(data.items || []));
  }, []);

  const createChallenge = async () => {
    await api.post("/users/challenges/create", {
      challenged_id: targetId,
      challenge_type: "xp_this_week",
      target_value: 300
    });
    const data = await api.get("/users/challenges");
    setChallenges(data.items || []);
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.eyebrow}>Challenges</div>
        <h2>Challenge a friend</h2>
        <p>Start a weekly XP battle.</p>
      </header>
      <div className={styles.card}>
        <input value={targetId} onChange={(event) => setTargetId(event.target.value)} placeholder="Friend user id" />
        <button type="button" onClick={createChallenge}>
          Send challenge
        </button>
      </div>
      <div className={styles.list}>
        {challenges.map((challenge) => (
          <div key={challenge._id} className={styles.row}>
            <span>{challenge.challenge_type}</span>
            <span>{challenge.status}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Challenges;

