import React, { useEffect, useMemo, useState } from "react";
import { api } from "../../api.js";
import styles from "./AdminDashboard.module.css";

const AdminDashboard = () => {
  const [stats, setStats] = useState({});
  const [sessions, setSessions] = useState([]);
  const [users, setUsers] = useState([]);

  useEffect(() => {
    api.get("/admin/stats").then(setStats).catch(() => {});
    api.get("/admin/sessions?limit=400").then((data) => setSessions(data.items || [])).catch(() => {});
    api.get("/admin/users?limit=400").then((data) => setUsers(data.items || [])).catch(() => {});
  }, []);

  const { sessionTypes, topLanguages, dailyActive } = useMemo(() => {
    const typeMap = {};
    const langMap = {};
    const activeMap = {};
    sessions.forEach((session) => {
      const type = session.session_type || "unknown";
      typeMap[type] = (typeMap[type] || 0) + 1;
      if (session.started_at) {
        const day = new Date(session.started_at).toISOString().slice(0, 10);
        if (!activeMap[day]) activeMap[day] = new Set();
        activeMap[day].add(session.user_id);
      }
    });

    users.forEach((user) => {
      const lang = user.target_language || "Unknown";
      langMap[lang] = (langMap[lang] || 0) + 1;
    });

    const dailySeries = [];
    for (let i = 29; i >= 0; i -= 1) {
      const date = new Date();
      date.setUTCDate(date.getUTCDate() - i);
      const key = date.toISOString().slice(0, 10);
      dailySeries.push({ date: key, value: activeMap[key] ? activeMap[key].size : 0 });
    }

    return {
      sessionTypes: Object.entries(typeMap),
      topLanguages: Object.entries(langMap).sort((a, b) => b[1] - a[1]).slice(0, 6),
      dailyActive: dailySeries
    };
  }, [sessions, users]);

  const maxDaily = Math.max(...dailyActive.map((item) => item.value), 1);
  const maxType = Math.max(...sessionTypes.map((item) => item[1]), 1);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <div className={styles.eyebrow}>Admin dashboard</div>
          <h1>System pulse</h1>
          <p>Live stats across LinguaAI in one glance.</p>
        </div>
      </header>

      <section className={styles.statsGrid}>
        <div className={styles.statCard}>
          <div className={styles.statLabel}>Total users</div>
          <div className={styles.statValue}>{stats.total_users ?? 0}</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statLabel}>Active today</div>
          <div className={styles.statValue}>{stats.active_today ?? 0}</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statLabel}>Active this week</div>
          <div className={styles.statValue}>{stats.active_week ?? 0}</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statLabel}>New this week</div>
          <div className={styles.statValue}>{stats.new_registrations ?? 0}</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statLabel}>Total sessions</div>
          <div className={styles.statValue}>{stats.total_sessions ?? 0}</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statLabel}>Sessions today</div>
          <div className={styles.statValue}>{stats.sessions_today ?? 0}</div>
        </div>
      </section>

      <section className={styles.charts}>
        <div className={styles.chartCard}>
          <h3>Daily active users</h3>
          <svg viewBox="0 0 300 120" className={styles.chart}>
            <polyline
              className={styles.chartLine}
              points={dailyActive
                .map((item, index) => {
                  const x = (index / (dailyActive.length - 1 || 1)) * 280 + 10;
                  const y = 100 - (item.value / maxDaily) * 80;
                  return `${x},${y}`;
                })
                .join(" ")}
            />
            {dailyActive.map((item, index) => {
              const x = (index / (dailyActive.length - 1 || 1)) * 280 + 10;
              const y = 100 - (item.value / maxDaily) * 80;
              return <circle key={item.date} cx={x} cy={y} r="2" className={styles.chartPoint} />;
            })}
          </svg>
        </div>

        <div className={styles.chartCard}>
          <h3>Sessions by type</h3>
          <div className={styles.barList}>
            {sessionTypes.map(([type, count]) => (
              <div key={type} className={styles.barRow}>
                <span>{type}</span>
                <div className={styles.barTrack}>
                  <div className={styles.barFill} style={{ width: `${(count / maxType) * 100}%` }} />
                </div>
                <span className={styles.barValue}>{count}</span>
              </div>
            ))}
          </div>
        </div>

        <div className={styles.chartCard}>
          <h3>Top target languages</h3>
          <div className={styles.langList}>
            {topLanguages.map(([lang, count]) => (
              <div key={lang} className={styles.langRow}>
                <div className={styles.langName}>{lang}</div>
                <div className={styles.barTrack}>
                  <div className={styles.barFill} style={{ width: `${Math.min(count * 10, 100)}%` }} />
                </div>
                <div className={styles.barValue}>{count}</div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
};

export default AdminDashboard;

