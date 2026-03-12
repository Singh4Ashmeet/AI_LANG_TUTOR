import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../../api.js";
import styles from "./AdminUserDetail.module.css";

const AdminUserDetail = () => {
  const { id } = useParams();
  const [user, setUser] = useState(null);
  const [cefr, setCefr] = useState("A1");
  const [role, setRole] = useState("user");
  const [status, setStatus] = useState(true);

  const load = async () => {
    const data = await api.get(`/admin/users/${id}`);
    setUser(data);
    setCefr(data.cefr_level || "A1");
    setRole(data.role || "user");
    setStatus(data.is_active ?? true);
  };

  useEffect(() => {
    load();
  }, [id]);

  const save = async () => {
    await api.put(`/admin/users/${id}`, { cefr_level: cefr, is_active: status });
    await load();
  };

  const updateRole = async () => {
    await api.put(`/admin/users/${id}/role`, { role });
    await load();
  };

  const toggleStatus = async () => {
    await api.put(`/admin/users/${id}/suspend`, { is_active: !status });
    await load();
  };

  const forceLogout = async () => {
    await api.delete(`/admin/users/${id}/session`);
  };

  const resetOtp = async () => {
    await api.post(`/admin/users/${id}/reset-otp`);
  };

  if (!user) return <div className={styles.loading}>Loading...</div>;

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h2>{user.username}</h2>
          <p>{user.email}</p>
        </div>
        <span className={`${styles.badge} ${user.is_active ? styles.active : styles.suspended}`}>
          {user.is_active ? "Active" : "Suspended"}
        </span>
      </header>

      <section className={styles.panel}>
        <h3>Edit profile</h3>
        <div className={styles.formGrid}>
          <label>
            CEFR level
            <select value={cefr} onChange={(event) => setCefr(event.target.value)}>
              {["A1", "A2", "B1", "B2", "C1", "C2"].map((level) => (
                <option key={level} value={level}>
                  {level}
                </option>
              ))}
            </select>
          </label>
          <label>
            Role
            <select value={role} onChange={(event) => setRole(event.target.value)}>
              <option value="user">User</option>
              <option value="admin">Admin</option>
            </select>
          </label>
          <label>
            Status
            <div className={styles.statusRow}>
              <span>{status ? "Active" : "Suspended"}</span>
              <button type="button" onClick={toggleStatus}>
                {status ? "Suspend" : "Unsuspend"}
              </button>
            </div>
          </label>
        </div>
        <div className={styles.actions}>
          <button type="button" onClick={save}>
            Save profile
          </button>
          <button type="button" className={styles.secondary} onClick={updateRole}>
            Apply role
          </button>
        </div>
      </section>

      <section className={styles.panel}>
        <h3>Admin actions</h3>
        <div className={styles.actions}>
          <button type="button" className={styles.secondary} onClick={forceLogout}>
            Force logout
          </button>
          <button type="button" className={styles.secondary} onClick={resetOtp}>
            Reset OTP
          </button>
        </div>
      </section>
    </div>
  );
};

export default AdminUserDetail;

