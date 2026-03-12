import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api.js";
import styles from "./AdminUsers.module.css";

const AdminUsers = () => {
  const [users, setUsers] = useState([]);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const loadUsers = () => {
    const params = new URLSearchParams();
    if (query) params.set("q", query);
    if (statusFilter !== "all") params.set("status_filter", statusFilter);
    api.get(`/admin/users?${params.toString()}`).then((data) => setUsers(data.items || []));
  };

  useEffect(() => {
    loadUsers();
  }, []);

  useEffect(() => {
    const handle = setTimeout(loadUsers, 300);
    return () => clearTimeout(handle);
  }, [query, statusFilter]);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h2>Users</h2>
          <p>Search, filter, and manage access.</p>
        </div>
      </header>
      <div className={styles.controls}>
        <input
          placeholder="Search username or email"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <div className={styles.filters}>
          {["all", "active", "suspended"].map((filter) => (
            <button
              key={filter}
              type="button"
              className={`${styles.chip} ${statusFilter === filter ? styles.active : ""}`}
              onClick={() => setStatusFilter(filter)}
            >
              {filter}
            </button>
          ))}
        </div>
      </div>

      <div className={styles.table}>
        <div className={styles.tableHeader}>
          <span>Username</span>
          <span>Email</span>
          <span>Language</span>
          <span>CEFR</span>
          <span>XP</span>
          <span>Streak</span>
          <span>Status</span>
          <span>Actions</span>
        </div>
        {users.map((user) => (
          <div key={user._id} className={styles.tableRow}>
            <span>{user.username}</span>
            <span>{user.email}</span>
            <span>{user.target_language || "—"}</span>
            <span>{user.cefr_level || "—"}</span>
            <span>{user.xp ?? 0}</span>
            <span>{user.streak ?? 0}</span>
            <span className={user.is_active ? styles.activeStatus : styles.suspendedStatus}>
              {user.is_active ? "Active" : "Suspended"}
            </span>
            <Link to={`/admin/users/${user._id}`} className={styles.linkButton}>
              View
            </Link>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AdminUsers;

