import React from "react";
import { NavLink } from "react-router-dom";
import styles from "./BottomNav.module.css";

const BottomNav = ({ ui }) => {
  const items = [
    { to: "/dashboard", label: ui.learn, icon: "\u{1F3E0}" },
    { to: "/tutor", label: ui.tutor, icon: "\u{1F5E3}\u{FE0F}" },
    { to: "/leaderboard", label: ui.league, icon: "\u{1F3C6}" },
    { to: "/practice", label: ui.practice, icon: "\u{1F4D6}" },
    { to: "/profile", label: ui.profile, icon: "\u{1F464}" },
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
