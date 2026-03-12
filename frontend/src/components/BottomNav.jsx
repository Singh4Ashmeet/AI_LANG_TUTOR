import React from "react";
import { NavLink } from "react-router-dom";
import styles from "./BottomNav.module.css";

const BottomNav = ({ ui }) => {
  const items = [
    { to: "/dashboard", label: ui.learn, icon: "🏠" },
    { to: "/tutor", label: ui.tutor, icon: "🗣️" },
    { to: "/leaderboard", label: ui.league, icon: "🏆" },
    { to: "/practice", label: ui.practice, icon: "📖" },
    { to: "/profile", label: ui.profile, icon: "👤" }
  ];

  return (
    <nav className={styles.nav}>
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ""}`}
        >
          <span className={styles.icon}>{item.icon}</span>
          <span className={styles.label}>{item.label}</span>
        </NavLink>
      ))}
    </nav>
  );
};

export default BottomNav;

