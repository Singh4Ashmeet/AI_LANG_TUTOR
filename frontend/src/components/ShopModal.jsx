import React, { useState } from "react";
import { api } from "../api.js";
import styles from "./ShopModal.module.css";

const ShopModal = ({ onClose, onUpdate }) => {
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");

  const buyFreeze = async () => {
    setLoading(true);
    setMsg("");
    try {
      await api.post("/users/me/buy-freeze");
      setMsg("Streak freeze equipped!");
      onUpdate();
    } catch (err) {
      setMsg(err.message || "Failed to buy.");
    } finally {
      setLoading(false);
    }
  };

  const refillHearts = async () => {
    setLoading(true);
    setMsg("");
    try {
      await api.post("/users/me/refill-hearts");
      setMsg("Hearts restored!");
      onUpdate();
    } catch (err) {
      setMsg(err.message || "Failed to refill.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.overlay}>
      <div className={styles.modal}>
        <div className={styles.header}>
          <h2>Item Shop</h2>
          <button className={styles.close} onClick={onClose}>
            &times;
          </button>
        </div>
        <div className={styles.grid}>
          <div className={styles.item}>
            <div className={styles.icon}>🧊</div>
            <h3>Streak Freeze</h3>
            <p>Protect your streak for one missed day.</p>
            <button disabled={loading} onClick={buyFreeze}>
              200 💎
            </button>
          </div>
          <div className={styles.item}>
            <div className={styles.icon}>❤️</div>
            <h3>Heart Refill</h3>
            <p>Restore full health immediately.</p>
            <button disabled={loading} onClick={refillHearts}>
              100 💎
            </button>
          </div>
        </div>
        {msg && <div className={styles.message}>{msg}</div>}
      </div>
    </div>
  );
};

export default ShopModal;
