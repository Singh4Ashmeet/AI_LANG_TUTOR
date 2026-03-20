import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import styles from "./PodcastMode.module.css";

const PodcastMode = () => {
  const [episode, setEpisode] = useState(null);
  const [summary, setSummary] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/bonus/podcast/start").then(setEpisode).catch((err) => setError(err.message));
  }, []);

  const submit = async () => {
    if (!episode) return;
    const data = await api.post(`/bonus/podcast/${episode.id}/submit`, { summary });
    setResult(data);
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.eyebrow}>Podcast Mode</div>
        <h2>{episode?.title || "Podcast listening"}</h2>
        <p>Read the dialogue, then write a quick summary.</p>
      </header>

      {error && <div className={styles.error}>{error}</div>}

      {episode && (
        <>
          <div className={styles.script}>{episode.script}</div>
          <label className={styles.label}>
            {episode.summary_prompt || "Write 3 sentences about what was discussed."}
            <textarea value={summary} onChange={(event) => setSummary(event.target.value)} rows={5} />
          </label>
          <button type="button" className={styles.submit} onClick={submit} disabled={summary.trim().length < 15}>
            Submit Summary
          </button>
        </>
      )}

      {result && <div className={styles.result}>XP +{result.xp}</div>}
    </div>
  );
};

export default PodcastMode;
