import React, { useEffect, useState } from "react";
import { api } from "../../api.js";
import styles from "./AdminDashboard.module.css";

const AdminDashboard = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/admin/stats")
      .then((data) => {
        setStats(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading || !stats) {
    return <div className={styles.loading}>Loading system pulse...</div>;
  }

  const dailyActive = stats.daily_active || [];
  const maxDaily = Math.max(...dailyActive.map((d) => d.count), 1);
  const sessionTypes = stats.session_types || [];
  const maxType = Math.max(...sessionTypes.map((t) => t.count), 1);
  const topLanguages = stats.top_languages || [];

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <div className={styles.eyebrow}>Admin dashboard</div>
          <h1>System pulse</h1>
          <p>Live stats across LinguAI in one glance.</p>
        </div>
      </header>

      <section className={styles.statsGrid}>
        <div className={styles.statCard}>
          <div className={styles.statLabel}>Total users</div>
          <div className={styles.statValue}>{stats.total_users?.toLocaleString() ?? 0}</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statLabel}>Active today</div>
          <div className={styles.statValue}>{stats.active_today?.toLocaleString() ?? 0}</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statLabel}>Active this week</div>
          <div className={styles.statValue}>{stats.active_week?.toLocaleString() ?? 0}</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statLabel}>New this week</div>
          <div className={styles.statValue}>{stats.new_registrations?.toLocaleString() ?? 0}</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statLabel}>Total sessions</div>
          <div className={styles.statValue}>{stats.total_sessions?.toLocaleString() ?? 0}</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statLabel}>Sessions today</div>
          <div className={styles.statValue}>{stats.sessions_today?.toLocaleString() ?? 0}</div>
        </div>
      </section>

      <section className={styles.charts}>
        <div className={styles.chartCard}>
          <div className={styles.chartHeader}>
            <h3>Daily active users</h3>
            <span className={styles.chartSub}>Last 30 days</span>
          </div>
          <div className={styles.svgWrapper}>
            <svg viewBox="0 0 400 160" className={styles.chart}>
              <defs>
                <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.3" />
                  <stop offset="100%" stopColor="#3b82f6" stopOpacity="0" />
                </linearGradient>
              </defs>
              {/* Grid Lines */}
              {[0, 0.25, 0.5, 0.75, 1].map((p) => (
                <line
                  key={p}
                  x1="0"
                  y1={140 - p * 120}
                  x2="400"
                  y2={140 - p * 120}
                  stroke="rgba(148, 163, 184, 0.1)"
                  strokeWidth="1"
                />
              ))}
              {/* Area */}
              <path
                className={styles.chartArea}
                fill="url(#areaGradient)"
                d={`M 0 140 ${dailyActive
                  .map((d, i) => {
                    const x = (i / (dailyActive.length - 1)) * 400;
                    const y = 140 - (d.count / maxDaily) * 120;
                    return `L ${x} ${y}`;
                  })
                  .join(" ")} L 400 140 Z`}
              />
              {/* Line */}
              <polyline
                className={styles.chartLine}
                points={dailyActive
                  .map((d, i) => {
                    const x = (i / (dailyActive.length - 1)) * 400;
                    const y = 140 - (d.count / maxDaily) * 120;
                    return `${x},${y}`;
                  })
                  .join(" ")}
              />
            </svg>
          </div>
        </div>

        <div className={styles.chartCard}>
          <h3>Sessions by type</h3>
          <div className={styles.barList}>
            {sessionTypes.map((st) => (
              <div key={st.type} className={styles.barRow}>
                <span className={styles.barLabel}>{st.type}</span>
                <div className={styles.barTrack}>
                  <div className={styles.barFill} style={{ width: `${(st.count / maxType) * 100}%` }} />
                </div>
                <span className={styles.barValue}>{st.count}</span>
              </div>
            ))}
          </div>
        </div>

        <div className={styles.chartCard}>
          <h3>Top target languages</h3>
          <div className={styles.barList}>
            {topLanguages.map((tl) => (
              <div key={tl.lang} className={styles.barRow}>
                <span className={styles.barLabel}>{tl.lang}</span>
                <div className={styles.barTrack}>
                  <div className={styles.barFill} style={{ width: `${(tl.count / stats.total_users || 1) * 100}%`, background: '#10b981' }} />
                </div>
                <span className={styles.barValue}>{tl.count}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className={styles.workflow}>
        <h3>Operational workflow</h3>
        <div className={styles.workflowGrid}>
          <div className={styles.workflowCard}>
            <strong>Input</strong>
            <span>Onboarding, lessons, chat, roleplay, voice, and practice events.</span>
          </div>
          <div className={styles.workflowCard}>
            <strong>Processing</strong>
            <span>Agent orchestration, error analysis, progression updates, and score computation.</span>
          </div>
          <div className={styles.workflowCard}>
            <strong>Storage</strong>
            <span>PostgreSQL records users, sessions, vocabulary, grammar, leaderboard, and logs.</span>
          </div>
          <div className={styles.workflowCard}>
            <strong>Controls</strong>
            <span>Admin can audit logs, edit users, force logout sessions, and test subsystems.</span>
          </div>
        </div>
      </section>
    </div>
  );
};

export default AdminDashboard;
