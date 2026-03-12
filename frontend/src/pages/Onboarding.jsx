import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";

const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "es", label: "Spanish" },
  { code: "fr", label: "French" },
  { code: "de", label: "German" },
  { code: "it", label: "Italian" },
  { code: "pt", label: "Portuguese" },
  { code: "ja", label: "Japanese" },
  { code: "ko", label: "Korean" },
  { code: "zh", label: "Mandarin" },
  { code: "ar", label: "Arabic" },
  { code: "ru", label: "Russian" },
  { code: "hi", label: "Hindi" }
];

const GOALS = [
  { id: "travel", label: "Travel" },
  { id: "career", label: "Career" },
  { id: "romance", label: "Romance" },
  { id: "family", label: "Family" },
  { id: "culture", label: "Culture" },
  { id: "academic", label: "Academic" }
];

const PERSONAS = [
  { id: "friendly", label: "Friendly" },
  { id: "strict", label: "Strict" },
  { id: "funny", label: "Funny" },
  { id: "professor", label: "Professor" }
];

const Onboarding = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [nativeLanguage, setNativeLanguage] = useState("en");
  const [targetLanguage, setTargetLanguage] = useState("es");
  const [goals, setGoals] = useState([]);
  const [persona, setPersona] = useState("friendly");
  const [dailyGoal, setDailyGoal] = useState(10);
  const [placement, setPlacement] = useState({ sessionId: null, question: "", index: 0 });
  const [placementAnswer, setPlacementAnswer] = useState("");
  const [placementResult, setPlacementResult] = useState(null);

  useEffect(() => {
    if (step === 5 && !placement.sessionId) {
      api.get("/placement/start").then((data) => {
        setPlacement({ sessionId: data.session_id, question: data.question, index: data.index });
      });
    }
  }, [step, placement.sessionId]);

  const toggleGoal = (goal) => {
    setGoals((prev) => (prev.includes(goal) ? prev.filter((g) => g !== goal) : [...prev, goal]));
  };

  const saveProfile = async () => {
    await api.post("/onboarding/complete", {
      native_language: nativeLanguage,
      target_language: targetLanguage,
      goals,
      tutor_persona: persona,
      daily_goal_minutes: dailyGoal
    });
  };

  const handlePlacementAnswer = async () => {
      const response = await api.post("/placement/respond", {
        session_id: placement.sessionId,
        answer: placementAnswer,
        index: placement.index
      });
      setPlacementAnswer("");
      if (response.done) {
        const result = await api.post("/placement/finish", {
          session_id: placement.sessionId
        });
        setPlacementResult(result);
        setStep(6);
      } else {
        setPlacement({ ...placement, question: response.question, index: response.index });
      }
  };

  return (
    <div className="page">
      <div className="page__inner">
        <div>
          <span className="pill">Setup</span>
          <h2 className="page__title">Onboarding</h2>
          <p className="page__subtitle">Let’s personalize your learning path.</p>
        </div>
      {step === 1 && (
        <div className="card card--play">
          <h3>Language Pair</h3>
          <div className="form-grid">
            <label>I speak</label>
            <select value={nativeLanguage} onChange={(event) => setNativeLanguage(event.target.value)}>
              {LANGUAGES.map((lang) => (
                <option key={lang.code} value={lang.code}>
                  {lang.label}
                </option>
              ))}
            </select>
            <label>I want to learn</label>
            <select value={targetLanguage} onChange={(event) => setTargetLanguage(event.target.value)}>
              {LANGUAGES.map((lang) => (
                <option key={lang.code} value={lang.code} disabled={lang.code === nativeLanguage}>
                  {lang.label}
                </option>
              ))}
            </select>
            <button className="btn btn--primary" onClick={() => setStep(2)}>
              Next
            </button>
          </div>
        </div>
      )}
      {step === 2 && (
        <div className="card">
          <h3>Goals</h3>
          <div className="playcard-grid">
            {GOALS.map((goal) => (
              <button
                key={goal.id}
                type="button"
                className={`playcard ${goals.includes(goal.id) ? "card--play" : ""}`}
                onClick={() => toggleGoal(goal.id)}
              >
                <div className="playcard__icon">🎯</div>
                <h3>{goal.label}</h3>
              </button>
            ))}
          </div>
          <button className="btn btn--primary" onClick={() => setStep(3)} disabled={goals.length === 0}>
            Next
          </button>
        </div>
      )}
      {step === 3 && (
        <div className="card">
          <h3>Tutor persona</h3>
          <div className="playcard-grid">
            {PERSONAS.map((item) => (
              <button
                key={item.id}
                type="button"
                className={`playcard ${persona === item.id ? "card--play" : ""}`}
                onClick={() => setPersona(item.id)}
              >
                <div className="playcard__icon">🧑‍🏫</div>
                <h3>{item.label}</h3>
              </button>
            ))}
          </div>
          <button className="btn btn--primary" onClick={() => setStep(4)}>
            Next
          </button>
        </div>
      )}
      {step === 4 && (
        <div className="card">
          <h3>Daily commitment</h3>
          <div className="stat-row">
            {[5, 10, 20, 30].map((value) => (
              <button
                key={value}
                type="button"
                className={dailyGoal === value ? "btn btn--primary" : "btn btn--ghost"}
                onClick={() => setDailyGoal(value)}
              >
                {value} min
              </button>
            ))}
          </div>
          <div style={{ marginTop: 16 }}>
            <button
              className="btn btn--primary"
              onClick={async () => {
                await saveProfile();
                setStep(5);
              }}
            >
              Start placement test
            </button>
          </div>
        </div>
      )}
      {step === 5 && (
        <div className="card">
          <h3>Placement test</h3>
          <p>Question {placement.index + 1} of 8</p>
          <div style={{ marginBottom: 12 }}>{placement.question}</div>
          <div className="form-grid">
            <input value={placementAnswer} onChange={(event) => setPlacementAnswer(event.target.value)} />
            <button className="btn btn--primary" onClick={handlePlacementAnswer}>
              Submit
            </button>
          </div>
        </div>
      )}
      {step === 6 && (
        <div className="card card--play">
          <h3>Done</h3>
          <p>Your level: {placementResult?.cefr_level || "A1"}</p>
          <button className="btn btn--primary" onClick={() => navigate("/dashboard")}>
            Start my first lesson
          </button>
        </div>
      )}
      </div>
    </div>
  );
};

export default Onboarding;
