import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import styles from "./Chat.module.css";

const Chat = () => {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.post("/chat/new").then((data) => setSessionId(data.session_id));
  }, []);

  const sendMessage = async () => {
    if (!input.trim() || !sessionId) return;
    const userMessage = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);
    const data = await api.post("/chat", { session_id: sessionId, message: userMessage.content, message_type: "text" });
    setMessages((prev) => [...prev, { role: "assistant", content: data.reply }]);
    setLoading(false);
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.eyebrow}>Live practice</div>
        <h2>Conversation room</h2>
        <p>Speak freely and get real-time coaching.</p>
      </header>
      <div className={styles.chatShell}>
        <div className={styles.chatWindow}>
          {messages.map((msg, idx) => (
            <div key={idx} className={`${styles.bubble} ${msg.role === "user" ? styles.user : styles.ai}`}>
              {msg.content}
            </div>
          ))}
          {loading && <div className={`${styles.bubble} ${styles.ai}`}>Typing...</div>}
        </div>
        <div className={styles.chatInput}>
          <input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Write in target language"
          />
          <button type="button" onClick={sendMessage} disabled={!sessionId || loading}>
            Send
          </button>
        </div>
      </div>
    </div>
  );
};

export default Chat;

