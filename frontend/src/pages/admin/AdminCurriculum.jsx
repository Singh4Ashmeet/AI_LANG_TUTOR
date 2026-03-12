import React, { useEffect, useState } from "react";
import { api } from "../../api.js";
import styles from "./AdminCurriculum.module.css";

const AdminCurriculum = () => {
  const [items, setItems] = useState([]);
  const [expanded, setExpanded] = useState(null);

  const load = async () => {
    const data = await api.get("/admin/curriculum");
    setItems(data.items || []);
  };

  useEffect(() => {
    load();
  }, []);

  const regenerate = async (pair) => {
    await api.post(`/admin/curriculum/regenerate/${pair}`);
    await load();
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h2>Curriculum</h2>
        <p>Manage cached curricula per language pair.</p>
      </header>
      <div className={styles.list}>
        {items.map((item) => (
          <div key={item._id} className={styles.card}>
            <div className={styles.cardHeader}>
              <div>
                <h3>{item.language_pair}</h3>
                <p>{item.sections?.length || 0} sections</p>
              </div>
              <div className={styles.actions}>
                <button type="button" onClick={() => regenerate(item.language_pair)}>
                  Regenerate
                </button>
                <button type="button" className={styles.secondary} onClick={() => setExpanded(item._id)}>
                  Preview
                </button>
              </div>
            </div>
            {expanded === item._id && (
              <div className={styles.preview}>
                {item.sections?.map((section) => (
                  <div key={section.section_index} className={styles.section}>
                    <h4>
                      Section {section.section_index + 1}: {section.title}
                    </h4>
                    <div className={styles.skills}>
                      {section.skills?.map((skill) => (
                        <div key={skill.skill_id} className={styles.skill}>
                          <span>{skill.emoji || "⭐"}</span>
                          <div>
                            <strong>{skill.title}</strong>
                            <p>{skill.description}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
                <button type="button" className={styles.secondary} onClick={() => setExpanded(null)}>
                  Close preview
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default AdminCurriculum;

