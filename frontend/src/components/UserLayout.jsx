import React, { useEffect, useMemo, useState } from "react";
import { Outlet } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../context/AuthContext.jsx";
import { getUiStrings } from "../utils/uiStrings.js";
import BottomNav from "./BottomNav.jsx";
import TopNav from "./TopNav.jsx";
import styles from "./UserLayout.module.css";

const UserLayout = () => {
  const { user } = useAuth();
  const [notifications, setNotifications] = useState([]);
  const [isOnline, setIsOnline] = useState(typeof navigator !== "undefined" ? navigator.onLine : true);

  const ui = useMemo(
    () => getUiStrings(user?.target_language, user?.immersion_mode),
    [user?.target_language, user?.immersion_mode]
  );

  useEffect(() => {
    document.documentElement.dataset.theme = user?.theme || "dark";
    document.documentElement.dataset.admin = "false";
  }, [user?.theme]);

  useEffect(() => {
    const update = () => setIsOnline(navigator.onLine);
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
    };
  }, []);

  useEffect(() => {
    if (!user) return;
    api.get("/notifications").then((data) => setNotifications(data.items || [])).catch(() => {});
  }, [user?._id]);

  const markAllRead = async () => {
    await api.post("/notifications/read-all");
    setNotifications((prev) => prev.map((item) => ({ ...item, read: true })));
  };

  return (
    <div className={styles.shell}>
      <TopNav user={user} ui={ui} notifications={notifications} onReadAll={markAllRead} />
      {!isOnline && <div className={styles.offline}>Offline Mode: cached lessons only.</div>}
      <main className={styles.main}>
        <Outlet />
      </main>
      <BottomNav ui={ui} />
    </div>
  );
};

export default UserLayout;

