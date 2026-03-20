import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import styles from "./Friends.module.css";

const Friends = () => {
  const [friends, setFriends] = useState([]);
  const [incoming, setIncoming] = useState([]);
  const [outgoing, setOutgoing] = useState([]);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);

  const load = async () => {
    const friendData = await api.get("/users/friends");
    setFriends(friendData.items || []);
    setIncoming(friendData.incoming || []);
    setOutgoing(friendData.outgoing || []);
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
        <h2>Build your language circle</h2>
        <p>Challenge friends, accept incoming requests, and keep motivation social.</p>
      </header>

      <section className={styles.summary}>
        <article className={styles.summaryCard}>
          <span>Friends</span>
          <strong>{friends.length}</strong>
        </article>
        <article className={styles.summaryCard}>
          <span>Incoming</span>
          <strong>{incoming.length}</strong>
        </article>
        <article className={styles.summaryCard}>
          <span>Pending sent</span>
          <strong>{outgoing.length}</strong>
        </article>
      </section>

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
        <h3>Incoming Requests</h3>
        <div className={styles.list}>
          {incoming.length === 0 && <p className={styles.empty}>No incoming requests right now.</p>}
          {incoming.map((request) => (
            <div key={request._id} className={styles.row}>
              <div className={styles.userInfo}>
                <span className={styles.username}>{request.user?.username}</span>
                <span className={styles.level}>{request.user?.cefr_level || "A1"} learner</span>
              </div>
              <button type="button" className={styles.addBtn} onClick={() => acceptFriend(request.user?._id)}>
                Accept
              </button>
            </div>
          ))}
        </div>
      </section>

      <section className={styles.section}>
        <h3>Pending Requests</h3>
        <div className={styles.list}>
          {outgoing.length === 0 && <p className={styles.empty}>No pending requests sent.</p>}
          {outgoing.map((request) => (
            <div key={request._id} className={styles.row}>
              <div className={styles.userInfo}>
                <span className={styles.username}>{request.user?.username}</span>
                <span className={styles.lang}>Waiting for reply</span>
              </div>
            </div>
          ))}
        </div>
      </section>

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
