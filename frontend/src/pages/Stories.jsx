import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import styles from "./Stories.module.css";

const Stories = () => {
  const [stories, setStories] = useState([]);
  const [selected, setSelected] = useState(null);
  const [content, setContent] = useState(null);

  useEffect(() => {
    api.get("/bonus/stories").then((data) => setStories(data.items || []));
  }, []);

  const openStory = (story) => {
    setSelected(story);
    setContent(story);
  };

  const completeStory = async () => {
    await api.post(`/bonus/stories/${selected.story_id}/complete`, { answers: [] });
    setSelected(null);
    const data = await api.get("/bonus/stories");
    setStories(data.items || []);
  };

  if (selected) {
    return (
      <div className={styles.page}>
        <div className={styles.storyCard}>
          <h2>{selected.title || "Story"}</h2>
          <pre className={styles.storyText}>{content?.story || JSON.stringify(content)}</pre>
          <button type="button" onClick={completeStory}>
            Mark complete
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.eyebrow}>Stories</div>
        <h2>Stories</h2>
        <p>Read short stories and answer questions.</p>
      </header>
      <div className={styles.grid}>
        {stories.map((story) => (
          <button key={story.story_id} className={styles.card} onClick={() => openStory(story)} type="button">
            <h3>{story.title || "Story"}</h3>
            <p>{story.description || "Practice reading and comprehension."}</p>
          </button>
        ))}
      </div>
    </div>
  );
};

export default Stories;

