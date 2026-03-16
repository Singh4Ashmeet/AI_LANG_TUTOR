import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import styles from "./Friends.module.css";

const Friends = () => {
  const [friends, setFriends] = useState([]);
  const [requests, setRequests] = useState([]);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);

  const load = async () => {
    const friendData = await api.get("/users/friends");
    setFriends(friendData.items || []);
    // We need a way to get pending requests. Let's assume the backend search can show status or we need a new endpoint.
    // For now, let's just implement the UI for the friends we have and the search results.
  };

  useEffect(() => {
    load();
  }, []);

  const search = async () => {
    const data = await api.get(`/users/search?q=${encodeURIComponent(query)}`);
    setResults(data.items || []);
  };

  const requestFriend = async (id) => {
    await api.post(`/users/friends/request/${id}`);
    search();
  };

  const acceptFriend = async (id) => {
    await api.post(`/users/friends/accept/${id}`);
    load();
  };

  const removeFriend = async (id) => {
    await api.delete(`/users/friends/${id}`);
    load();
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.eyebrow}>Friends</div>
        <h2>Social Circle</h2>
        <p>Connect with other learners to stay motivated.</p>
      </header>

      <div className={styles.search}>
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search by username or email" />
        <button type="button" onClick={search}>
          Search
        </button>
      </div>

      {results.length > 0 && (
        <section className={styles.section}>
          <h3>Search Results</h3>
          <div className={styles.list}>
            {results.map((user) => (
              <div key={user._id} className={styles.row}>
                <div className={styles.userInfo}>
                  <span className={styles.username}>{user.username}</span>
                  <span className={styles.level}>{user.cefr_level || "A1"}</span>
                </div>
                <button type="button" className={styles.addBtn} onClick={() => requestFriend(user._id)}>
                  Add Friend
                </button>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className={styles.section}>
        <h3>Your Friends ({friends.length})</h3>
        <div className={styles.list}>
          {friends.length === 0 && <p className={styles.empty}>No friends yet. Start searching!</p>}
          {friends.map((friend) => (
            <div key={friend._id} className={styles.row}>
              <div className={styles.userInfo}>
                <span className={styles.username}>{friend.username}</span>
                <span className={styles.lang}>{friend.target_language}</span>
              </div>
              <button type="button" className={styles.removeBtn} onClick={() => removeFriend(friend._id)}>
                Remove
              </button>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
};

export default Friends;

