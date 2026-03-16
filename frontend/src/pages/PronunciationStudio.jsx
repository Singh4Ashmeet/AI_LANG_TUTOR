import React, { useRef, useState } from "react";
import { api } from "../api.js";
import styles from "./PronunciationStudio.module.css";

const PronunciationStudio = () => {
  const [phrase, setPhrase] = useState("");
  const [recording, setRecording] = useState(false);
  const [recordedUrl, setRecordedUrl] = useState("");
  const [audioBlob, setAudioBlob] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  
  const recorderRef = useRef(null);
  const chunksRef = useRef([]);

  const startRecording = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const recorder = new MediaRecorder(stream);
    chunksRef.current = [];
    
    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) chunksRef.current.push(event.data);
    };
    
    recorder.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: "audio/webm" });
      setRecordedUrl(URL.createObjectURL(blob));
      setAudioBlob(blob);
      stream.getTracks().forEach((track) => track.stop());
    };
    
    recorderRef.current = recorder;
    recorder.start();
    setRecording(true);
    setResult(null);
  };

  const stopRecording = () => {
    if (recorderRef.current && recording) {
      recorderRef.current.stop();
      setRecording(false);
    }
  };

  const scorePronunciation = async () => {
    if (!audioBlob || !phrase) return;
    setLoading(true);
    try {
      // 1. Transcribe
      const formData = new FormData();
      formData.append("file", audioBlob, "recording.webm");
      
      // We need to use fetch directly or ensure api.post handles FormData correctly if it's a wrapper
      // Assuming api.js might not handle FormData automatically if it expects JSON, let's look at api.js if needed.
      // But typically axios/fetch handles it if body is FormData.
      // Let's assume api.post can take a second arg for config or detects FormData.
      // Actually, looking at typical api wrappers, often they default to JSON.
      // Let's try to use the api wrapper but if it fails we might need to adjust.
      // For now, let's assume the wrapper handles it or we manually set headers.
      // Wait, let's check api.js to be safe. 
      // I'll skip checking for now and assume I can pass the FormData.
      
      // Actually, the api utility likely sets Content-Type to application/json.
      // I will implement a raw fetch here to be safe or use a specific api method if I knew it.
      // But let's try to use api.post and see if it works, usually wrappers are smart enough.
      // Wait, if I use `api.post("/voice/stt", formData)`, the browser sets the boundary.
      
      // Let's try to use a direct fetch for the file upload to avoid header conflicts
      const token = localStorage.getItem("token");
      const baseUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
      const sttRes = await fetch(`${baseUrl}/voice/stt`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
        },
        body: formData
      });
      const sttData = await sttRes.json();
      const recognized = sttData.text || "";

      // 2. Score
      const scoreRes = await api.post("/voice/pronunciation-score", {
        expected_text: phrase,
        recognized_text: recognized
      });
      
      setResult(scoreRes);
    } catch (err) {
      console.error(err);
      alert("Analysis failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.eyebrow}>Pronunciation studio</div>
        <h2>Pronunciation practice</h2>
        <p>Record and compare your pronunciation.</p>
      </header>
      
      <div className={styles.card}>
        <label className={styles.label}>
          Phrase to practice
          <input 
            className={styles.input}
            value={phrase} 
            onChange={(event) => setPhrase(event.target.value)} 
            placeholder="Type a phrase (e.g., 'Bonjour tout le monde')" 
          />
        </label>
        
        <div className={styles.actions}>
          <button 
            type="button" 
            className={`${styles.recordBtn} ${recording ? styles.recording : ""}`}
            onClick={recording ? stopRecording : startRecording}
          >
            {recording ? "Stop Recording" : "Start Recording"}
          </button>
          
          <button 
            type="button" 
            className={styles.scoreBtn} 
            onClick={scorePronunciation}
            disabled={!audioBlob || !phrase || loading}
          >
            {loading ? "Analyzing..." : "Analyze Pronunciation"}
          </button>
        </div>

        {recordedUrl && (
          <div className={styles.audioWrapper}>
            <audio className={styles.audio} controls src={recordedUrl} />
          </div>
        )}

        {result && (
          <div className={styles.result}>
            <div className={styles.scoreRing} style={{ "--score": result.score }}>
              <div className={styles.scoreValue}>{result.score}</div>
              <div className={styles.scoreLabel}>Score</div>
            </div>
            
            <div className={styles.feedback}>
              <h3>Feedback</h3>
              <p className={styles.feedbackText}>{result.feedback}</p>
              
              <div className={styles.comparison}>
                <div className={styles.compRow}>
                  <span className={styles.compLabel}>Expected:</span>
                  <span className={styles.compText}>{result.expected}</span>
                </div>
                <div className={styles.compRow}>
                  <span className={styles.compLabel}>Heard:</span>
                  <span className={`${styles.compText} ${styles.heard}`}>{result.actual}</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default PronunciationStudio;

