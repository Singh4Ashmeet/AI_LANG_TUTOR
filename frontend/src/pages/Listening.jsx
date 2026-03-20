import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import { useAuth } from "../context/AuthContext.jsx";
import styles from "./Listening.module.css";

const Listening = () => {
  const { user } = useAuth();
  const [challenge, setChallenge] = useState(null);
  const [answer, setAnswer] = useState("");
  const [result, setResult] = useState(null);

  useEffect(() => {
    api.get("/bonus/listening/1").then(setChallenge).catch(() => {});
  }, []);

  const speak = (text, slow = false) => {
    if (!text || !("speechSynthesis" in window)) return;
    const utterance = new SpeechSynthesisUtterance(slow ? text.split("").join(" ") : text);
    const langMap = {
      english: "en-US",
      spanish: "es-ES",
      french: "fr-FR",
      german: "de-DE",
      italian: "it-IT",
      japanese: "ja-JP",
      korean: "ko-KR",
      hindi: "hi-IN",
      portuguese: "pt-PT"
    };
    utterance.lang = langMap[(user?.target_language || "").toLowerCase()] || "en-US";
    utterance.rate = slow ? 0.65 : 0.95;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
  };

  const submit = async () => {
    if (!challenge) return;
    const data = await api.post(`/bonus/listening/${challenge.id}/submit`, { answer });
    setResult(data);
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <div className={styles.eyebrow}>Listening</div>
          <h2>Dictation practice</h2>
          <p>Listen, type what you hear, and get feedback that distinguishes tiny spelling slips from bigger misses.</p>
        </div>
        <div className={styles.badge}>{challenge?.focus || "listening focus"}</div>
      </header>

      <div className={styles.layout}>
        <section className={styles.card}>
          <div className={styles.promptRow}>
            <div>
              <span className={styles.label}>Prompt</span>
              <h3>{challenge?.prompt || "Loading..."}</h3>
            </div>
            <div className={styles.controls}>
              <button type="button" className={styles.audio} onClick={() => speak(challenge?.audio_text)}>
                Play
              </button>
              <button type="button" className={styles.audioAlt} onClick={() => speak(challenge?.audio_text, true)}>
                Slow
              </button>
            </div>
          </div>

          <textarea
            value={answer}
            onChange={(event) => setAnswer(event.target.value)}
            placeholder="Type exactly what you hear"
          />

          <div className={styles.actionRow}>
            <button type="button" className={styles.primary} onClick={submit}>
              Check answer
            </button>
            {challenge?.hint && <div className={styles.hintShell}>Hint: {challenge.hint}</div>}
          </div>

          {result && (
            <div className={styles.resultCard}>
              <div className={result.correct ? styles.success : styles.warning}>
                {result.accepted_with_typo
                  ? "Accepted with a small spelling slip"
                  : result.correct
                    ? "Great listening"
                    : result.almost_correct
                      ? "Very close"
                      : "Keep listening"}
              </div>
              <div className={styles.resultMeta}>XP earned: {result.xp}</div>
              {!result.correct && <div className={styles.correctText}>Correct text: {result.correct_text}</div>}
              {result.hint && <div className={styles.followup}>Try again by focusing on the stressed word or ending.</div>}
            </div>
          )}
        </section>

        <aside className={styles.sidebar}>
          <div className={styles.sidebarCard}>
            <span>How to improve</span>
            <p>Listen once for the whole phrase, then again for endings, names, and function words. Slow mode helps you hear spelling details without turning the task into pure reading.</p>
          </div>
          <div className={styles.sidebarCard}>
            <span>Why this feels better</span>
            <p>The app now treats tiny dictation slips differently from full misses, which is much closer to the way Duolingo keeps learners moving without feeling punished.</p>
          </div>
        </aside>
      </div>
    </div>
  );
};

export default Listening;
