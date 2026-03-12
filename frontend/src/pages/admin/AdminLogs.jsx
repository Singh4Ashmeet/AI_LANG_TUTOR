import React, { useEffect, useState } from "react";
import { api } from "../../api.js";
import styles from "./AdminLogs.module.css";

const AdminLogs = () => {
  const [logs, setLogs] = useState([]);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    const params = filter ? `?event_type=${encodeURIComponent(filter)}` : "";
    api.get(`/admin/logs${params}`).then((data) => setLogs(data.items || []));
  }, [filter]);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h2>Logs</h2>
        <p>Trace system activity and errors.</p>
      </header>
      <div className={styles.controls}>
        <input
          placeholder="Filter by event type"
          value={filter}
          onChange={(event) => setFilter(event.target.value)}
        />
      </div>
      <div className={styles.table}>
        <div className={styles.tableHeader}>
          <span>Type</span>
          <span>Message</span>
          <span>Time</span>
        </div>
        {logs.map((log) => (
          <div key={log._id} className={styles.tableRow}>
            <span>{log.event_type}</span>
            <span>{log.message}</span>
            <span>{log.created_at ? new Date(log.created_at).toLocaleString() : "—"}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AdminLogs;

