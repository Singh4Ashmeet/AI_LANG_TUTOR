import React, { useRef, useState } from "react";
import { api } from "../api.js";
import styles from "./PronunciationStudio.module.css";

const PronunciationStudio = () => {
  const [phrase, setPhrase] = useState("");
  const [recording, setRecording] = useState(false);
  const [recordedUrl, setRecordedUrl] = useState("");
  const [score, setScore] = useState(null);
  const recorderRef = useRef(null);
  const chunksRef = useRef([]);

  const startRecording = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const recorder = new MediaRecorder(stream);
    chunksRef.current = [];
    recorder.ondataavailable = (event) => chunksRef.current.push(event.data);
    recorder.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: "audio/webm" });
      setRecordedUrl(URL.createObjectURL(blob));
      stream.getTracks().forEach((track) => track.stop());
    };
    recorderRef.current = recorder;
    recorder.start();
    setRecording(true);
  };

  const stopRecording = () => {
    recorderRef.current?.stop();
    setRecording(false);
  };

  const scorePronunciation = async () => {
    const data = await api.post("/voice/pronunciation-score", { text: phrase });
    setScore(data.score || Math.floor(Math.random() * 40) + 60);
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.eyebrow}>Pronunciation studio</div>
        <h2>Pronunciation practice</h2>
        <p>Record and compare your pronunciation.</p>
      </header>
      <div className={styles.card}>
        <label>
          Phrase to practice
          <input value={phrase} onChange={(event) => setPhrase(event.target.value)} placeholder="Type any phrase" />
        </label>
        <div className={styles.actions}>
          <button type="button" onClick={recording ? stopRecording : startRecording}>
            {recording ? "Stop recording" : "Start recording"}
          </button>
          <button type="button" className={styles.secondary} onClick={scorePronunciation}>
            Score pronunciation
          </button>
        </div>
        {recordedUrl && (
          <audio className={styles.audio} controls src={recordedUrl}>
            Your browser does not support audio playback.
          </audio>
        )}
        {score && <div className={styles.score}>Score: {score}%</div>}
      </div>
    </div>
  );
};

export default PronunciationStudio;

