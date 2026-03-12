import React, { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../context/AuthContext.jsx";
import styles from "./Lesson.module.css";

const Lesson = () => {
  const navigate = useNavigate();
  const { skill, n } = useParams();
  const { user } = useAuth();
  const lessonIndex = Number(n || 0);
  const [sessionId, setSessionId] = useState(null);
  const [exercises, setExercises] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [feedback, setFeedback] = useState(null);
  const [hearts, setHearts] = useState(user?.hearts ?? 5);
  const [textAnswer, setTextAnswer] = useState("");
  const [selectedChoice, setSelectedChoice] = useState("");
  const [orderAnswer, setOrderAnswer] = useState([]);
  const [matchAnswer, setMatchAnswer] = useState({});
  const [recording, setRecording] = useState(false);
  const [recorded, setRecorded] = useState(false);
  const [tipCards, setTipCards] = useState([]);
  const [tipIndex, setTipIndex] = useState(0);
  const [showTips, setShowTips] = useState(false);
  const recorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  const exercise = exercises[currentIndex];
  const type = Number(exercise?.type || 0);
  const choices = useMemo(() => (Array.isArray(exercise?.choices) ? exercise.choices : []), [exercise]);
  const progress = exercises.length ? (currentIndex / exercises.length) * 100 : 0;

  useEffect(() => {
    const loadTips = async () => {
      if (lessonIndex === 0) {
        const tipData = await api.get(`/curriculum/skill/${skill}`);
        const tips = tipData.tip_cards || [];
        if (tips.length) {
          setTipCards(tips);
          setShowTips(true);
        }
      }
    };
    loadTips().catch(() => {});
  }, [skill, lessonIndex]);

  useEffect(() => {
    const loadLesson = async () => {
      if (!navigator.onLine) {
        const cache = JSON.parse(localStorage.getItem("offline_lessons") || "[]");
        const cached = cache.find(
          (item) => Number(item.skill_id) === Number(skill) && Number(item.lesson_index) === lessonIndex
        );
        if (cached) {
          setExercises(cached.exercises || []);
          setSessionId(cached.session_id || null);
        }
        return;
      }

      const data = await api.post("/lessons/start", { skill_id: Number(skill), lesson_index: lessonIndex });
      setSessionId(data.session_id);
      setExercises(data.exercises || []);

      const existing = JSON.parse(localStorage.getItem("offline_lessons") || "[]");
      const nextCache = [
        { skill_id: Number(skill), lesson_index: lessonIndex, exercises: data.exercises, session_id: data.session_id },
        ...existing.filter(
          (item) => Number(item.skill_id) !== Number(skill) || Number(item.lesson_index) !== lessonIndex
        )
      ].slice(0, 2);
      localStorage.setItem("offline_lessons", JSON.stringify(nextCache));
    };
    loadLesson().catch(() => {});
  }, [skill, lessonIndex]);

  const resetAnswerState = () => {
    setTextAnswer("");
    setSelectedChoice("");
    setOrderAnswer([]);
    setMatchAnswer({});
    setRecorded(false);
  };

  const playTone = (frequency) => {
    try {
      const ctx = new AudioContext();
      const oscillator = ctx.createOscillator();
      const gain = ctx.createGain();
      oscillator.type = "sine";
      oscillator.frequency.value = frequency;
      gain.gain.value = 0.06;
      oscillator.connect(gain);
      gain.connect(ctx.destination);
      oscillator.start();
      setTimeout(() => {
        oscillator.stop();
        ctx.close();
      }, 140);
    } catch (err) {
      // ignore
    }
  };

  const playSpeech = (text) => {
    if (!text || !("speechSynthesis" in window)) return;
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = "en-US";
    window.speechSynthesis.speak(utter);
  };

  const startRecording = async () => {
    if (!navigator.mediaDevices?.getUserMedia) return;
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const recorder = new MediaRecorder(stream);
    audioChunksRef.current = [];
    recorder.ondataavailable = (event) => {
      audioChunksRef.current.push(event.data);
    };
    recorder.onstop = () => {
      setRecorded(true);
      stream.getTracks().forEach((track) => track.stop());
    };
    recorderRef.current = recorder;
    recorder.start();
    setRecording(true);
  };

  const stopRecording = () => {
    if (recorderRef.current && recording) {
      recorderRef.current.stop();
      setRecording(false);
    }
  };

  const submitAnswer = async (payload) => {
    if (!sessionId || !exercise) return;
    const data = await api.post("/lessons/exercise/answer", {
      session_id: sessionId,
      exercise_index: currentIndex,
      user_answer: payload
    });
    setHearts(data.hearts_remaining);
    setFeedback(data);
    playTone(data.is_correct ? 880 : 240);
  };

  const continueLesson = async () => {
    setFeedback(null);
    resetAnswerState();
    const next = currentIndex + 1;
    if (next >= exercises.length) {
      const result = await api.post("/lessons/complete", { session_id: sessionId });
      navigate("/lesson/complete", { state: { ...result, hearts } });
      return;
    }
    setCurrentIndex(next);
  };

  const handleCheck = async () => {
    if (!exercise) return;
    if (type === 1) {
      submitAnswer("");
      return;
    }
    if (type === 6) {
      submitAnswer(matchAnswer);
      return;
    }
    if (type === 7) {
      submitAnswer(recorded ? "voice" : "voice_unrecorded");
      return;
    }
    if (type === 8) {
      submitAnswer(orderAnswer);
      return;
    }
    if (choices.length) {
      submitAnswer(selectedChoice);
      return;
    }
    submitAnswer(textAnswer);
  };

  if (showTips) {
    const tip = tipCards[tipIndex];
    return (
      <div className={styles.page}>
        <div className={styles.tips}>
          <div className={styles.tipCard}>
            <div className={styles.tipHeader}>Skill tips</div>
            <h2>{tip?.title}</h2>
            <p>{tip?.explanation}</p>
            <div className={styles.examples}>
              {tip?.examples?.map((example, index) => (
                <div key={`${example.target}-${index}`} className={styles.exampleRow}>
                  <span>{example.target}</span>
                  <span>{example.native}</span>
                </div>
              ))}
            </div>
          </div>
          <div className={styles.tipControls}>
            <button
              type="button"
              className={styles.secondary}
              disabled={tipIndex === 0}
              onClick={() => setTipIndex((prev) => Math.max(0, prev - 1))}
            >
              Previous
            </button>
            {tipIndex < tipCards.length - 1 ? (
              <button type="button" onClick={() => setTipIndex((prev) => Math.min(tipCards.length - 1, prev + 1))}>
                Next
              </button>
            ) : (
              <button type="button" onClick={() => setShowTips(false)}>
                Start lesson
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  if (!exercise) {
    return <div className={styles.loading}>Loading lesson...</div>;
  }

  return (
    <div className={styles.page}>
      <div className={styles.topBar}>
        <div className={styles.progress}>
          <div className={styles.progressFill} style={{ width: `${progress}%` }} />
        </div>
        <div className={styles.hearts}>
          {[...Array(5)].map((_, index) => (
            <span key={index} className={`${styles.heart} ${index < hearts ? styles.full : ""}`}>
              ♥
            </span>
          ))}
        </div>
      </div>

      <div className={styles.exercise}>
        <div className={styles.prompt}>{exercise.content || exercise.prompt || "Exercise"}</div>
        {exercise.audio_text && (
          <button type="button" className={styles.audioButton} onClick={() => playSpeech(exercise.audio_text)}>
            Play audio
          </button>
        )}

        {type === 1 && (
          <div className={styles.intro}>
            <p>Read and continue when ready.</p>
          </div>
        )}

        {choices.length > 0 && type !== 8 && type !== 6 && (
          <div className={styles.choiceGrid}>
            {choices.map((choice, index) => (
              <button
                key={`${choice}-${index}`}
                type="button"
                className={`${styles.choice} ${selectedChoice === choice ? styles.choiceActive : ""}`}
                onClick={() => setSelectedChoice(choice)}
              >
                {choice}
              </button>
            ))}
          </div>
        )}

        {choices.length === 0 && type !== 6 && type !== 7 && type !== 8 && (
          <div className={styles.inputRow}>
            <input
              value={textAnswer}
              onChange={(event) => setTextAnswer(event.target.value)}
              placeholder="Type your answer"
            />
          </div>
        )}

        {type === 6 && (
          <div className={styles.matchGrid}>
            {choices.map((pair, index) => (
              <div key={index} className={styles.matchRow}>
                <span>{pair.left || pair[0]}</span>
                <select
                  value={matchAnswer[pair.left || pair[0]] || ""}
                  onChange={(event) =>
                    setMatchAnswer((prev) => ({ ...prev, [pair.left || pair[0]]: event.target.value }))
                  }
                >
                  <option value="">Select</option>
                  {choices.map((option) => (
                    <option key={option.right || option[1]} value={option.right || option[1]}>
                      {option.right || option[1]}
                    </option>
                  ))}
                </select>
              </div>
            ))}
          </div>
        )}

        {type === 7 && (
          <div className={styles.voice}>
            <button type="button" onClick={recording ? stopRecording : startRecording}>
              {recording ? "Stop recording" : "Start recording"}
            </button>
            <div className={styles.voiceStatus}>{recorded ? "Recording saved" : "No recording yet"}</div>
          </div>
        )}

        {type === 8 && (
          <div className={styles.order}>
            <div className={styles.orderChoices}>
              {choices.map((word) => (
                <button
                  key={word}
                  type="button"
                  className={styles.wordChip}
                  onClick={() => setOrderAnswer((prev) => [...prev, word])}
                >
                  {word}
                </button>
              ))}
            </div>
            <div className={styles.orderAnswer}>
              {orderAnswer.map((word, index) => (
                <span key={`${word}-${index}`} className={styles.wordChip}>
                  {word}
                </span>
              ))}
            </div>
            <button type="button" className={styles.secondary} onClick={() => setOrderAnswer([])}>
              Reset order
            </button>
          </div>
        )}
      </div>

      <div className={styles.actions}>
        {!feedback && (
          <button type="button" className={styles.primary} onClick={handleCheck}>
            Check
          </button>
        )}
        {feedback && (
          <div className={styles.feedback}>
            <div className={feedback.is_correct ? styles.correct : styles.incorrect}>
              {feedback.is_correct ? "Correct!" : "Not quite."}
            </div>
            {!feedback.is_correct && (
              <div className={styles.explanation}>Correct answer: {String(feedback.correct_answer)}</div>
            )}
            {feedback.explanation && <div className={styles.explanation}>{feedback.explanation}</div>}
            <button type="button" className={styles.primary} onClick={continueLesson}>
              Continue
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default Lesson;

