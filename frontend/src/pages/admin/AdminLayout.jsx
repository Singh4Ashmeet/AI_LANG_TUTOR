import React, { useEffect } from "react";
import { Link, NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../../context/AuthContext.jsx";
import styles from "./AdminLayout.module.css";

const AdminLayout = () => {
  const { logout } = useAuth();

  useEffect(() => {
    document.documentElement.dataset.admin = "true";
  }, []);

  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        <div className={styles.logo}>LinguAI Admin</div>
        <nav className={styles.nav}>
          <NavLink to="/admin" end className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ""}`}>
            📊 Dashboard
          </NavLink>
          <NavLink to="/admin/users" className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ""}`}>
            👥 Users
          </NavLink>
          <NavLink to="/admin/sessions" className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ""}`}>
            📚 Sessions
          </NavLink>
          <NavLink to="/admin/curriculum" className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ""}`}>
            🌍 Curriculum
          </NavLink>
          <NavLink to="/admin/leaderboard" className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ""}`}>
            🏆 Leaderboard
          </NavLink>
          <NavLink to="/admin/logs" className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ""}`}>
            📝 Logs
          </NavLink>
          <NavLink to="/admin/system" className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ""}`}>
            ⚙️ System
          </NavLink>
          <div className={styles.divider} />
          <Link to="/dashboard" className={styles.link}>
            🔗 View User App
          </Link>
          <button className={styles.logout} onClick={logout} type="button">
            🚪 Logout
          </button>
        </nav>
      </aside>
      <main className={styles.main}>
        <Outlet />
      </main>
    </div>
  );
};

export default AdminLayout;
