import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import styles from "./Roleplay.module.css";

const scenarios = [
  { id: "restaurant", name: "Restaurant", description: "Order food and ask questions.", difficulty: "A1-A2" },
  { id: "airport", name: "Airport", description: "Check in and ask for directions.", difficulty: "A2" },
  { id: "interview", name: "Interview", description: "Handle common interview prompts.", difficulty: "B1" },
  { id: "hotel", name: "Hotel", description: "Book a room and request help.", difficulty: "A2" },
  { id: "doctor", name: "Doctor", description: "Explain symptoms and get advice.", difficulty: "B1" },
  { id: "shopping", name: "Shopping", description: "Ask about prices and sizes.", difficulty: "A1-A2" },
  { id: "landlord", name: "Landlord", description: "Discuss repairs and rent.", difficulty: "B1" },
  { id: "coffee", name: "Coffee chat", description: "Small talk and ordering.", difficulty: "A1" }
];

const Roleplay = () => {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [selected, setSelected] = useState(scenarios[0]);
  const [customPrompt, setCustomPrompt] = useState("");

  const startScenario = async () => {
    const data = await api.post("/roleplay/new", { scenario: selected.name });
    setSessionId(data.session_id);
  };

  const startCustom = async () => {
    const data = await api.post("/roleplay/custom", { prompt: customPrompt });
    setSessionId(data.session_id);
  };

  const sendMessage = async () => {
    if (!input.trim() || !sessionId) return;
    const userMessage = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    const data = await api.post("/roleplay", { session_id: sessionId, message: userMessage.content });
    setMessages((prev) => [...prev, { role: "assistant", content: data.reply }]);
  };

  if (!sessionId) {
    return (
      <div className={styles.page}>
        <header className={styles.header}>
          <div className={styles.eyebrow}>Roleplay studio</div>
          <h2>Choose a scenario</h2>
          <p>Practice real moments with playful coaching.</p>
        </header>
        <div className={styles.grid}>
          {scenarios.map((scenario) => (
            <button
              key={scenario.id}
              type="button"
              className={`${styles.card} ${selected.id === scenario.id ? styles.active : ""}`}
              onClick={() => setSelected(scenario)}
            >
              <h3>{scenario.name}</h3>
              <p>{scenario.description}</p>
              <span>{scenario.difficulty}</span>
            </button>
          ))}
        </div>
        <div className={styles.actions}>
          <button type="button" onClick={startScenario}>
            Start scenario
          </button>
          <div className={styles.custom}>
            <input
              placeholder="I want to practice..."
              value={customPrompt}
              onChange={(event) => setCustomPrompt(event.target.value)}
            />
            <button type="button" onClick={startCustom} disabled={!customPrompt.trim()}>
              Create scenario
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.eyebrow}>Roleplay live</div>
        <h2>{selected.name} session</h2>
        <p>Stay in character and keep the flow going.</p>
      </header>
      <div className={styles.chatShell}>
        <div className={styles.chatWindow}>
          {messages.map((msg, idx) => (
            <div key={idx} className={`${styles.bubble} ${msg.role === "user" ? styles.user : styles.ai}`}>
              {msg.content}
            </div>
          ))}
        </div>
        <div className={styles.chatInput}>
          <input value={input} onChange={(event) => setInput(event.target.value)} />
          <button type="button" onClick={sendMessage}>
            Send
          </button>
        </div>
      </div>
    </div>
  );
};

export default Roleplay;

