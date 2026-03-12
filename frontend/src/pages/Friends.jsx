import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import styles from "./Friends.module.css";

const Friends = () => {
  const [friends, setFriends] = useState([]);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);

  useEffect(() => {
    api.get("/users/friends").then((data) => setFriends(data.items || []));
  }, []);

  const search = async () => {
    const data = await api.get(`/users/search?q=${encodeURIComponent(query)}`);
    setResults(data.items || []);
  };

  const requestFriend = async (id) => {
    await api.post(`/users/friends/request/${id}`);
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.eyebrow}>Friends</div>
        <h2>Find friends</h2>
        <p>Challenge friends and share progress.</p>
      </header>
      <div className={styles.search}>
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search users" />
        <button type="button" onClick={search}>
          Search
        </button>
      </div>
      <div className={styles.list}>
        {results.map((user) => (
          <div key={user._id} className={styles.row}>
            <span>{user.username}</span>
            <button type="button" onClick={() => requestFriend(user._id)}>
              Add
            </button>
          </div>
        ))}
      </div>
      <div className={styles.list}>
        {friends.map((friend) => (
          <div key={friend._id} className={styles.row}>
            <span>{friend.username}</span>
            <span>{friend.target_language || ""}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Friends;

