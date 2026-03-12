import React, { useMemo } from "react";
import { Link } from "react-router-dom";
import styles from "./PathMap.module.css";

const PathMap = ({ sections, user }) => {
  const { items, activeIndex } = useMemo(() => {
    const flattened = [];
    sections.forEach((section, sectionIndex) => {
      section.skills?.forEach((skill, skillIndex) => {
        flattened.push({ ...skill, sectionIndex, skillIndex });
      });
      flattened.push({ chest: true, sectionIndex });
    });

    const path = user?.path_position || {};
    const activeSection = path.section_index ?? 0;
    const activeSkill = path.skill_index ?? 0;
    let computedActive = 0;
    flattened.forEach((item, index) => {
      if (item.chest) return;
      if (item.sectionIndex === activeSection && item.skillIndex === activeSkill) {
        computedActive = index;
      }
    });
    return { items: flattened, activeIndex: computedActive };
  }, [sections, user?.path_position]);

  return (
    <div className={styles.map}>
      <div className={styles.pathLine} />
      <div className={styles.nodes}>
        {items.map((item, index) => {
          const alignment = index % 3;
          if (item.chest) {
            return (
              <div key={`chest-${item.sectionIndex}`} className={`${styles.node} ${styles.chest}`}>
                <div className={styles.chestShell}>
                  <div className={styles.chestLid} />
                  <div className={styles.chestBody} />
                </div>
                <div className={styles.chestLabel}>Section {item.sectionIndex + 1} chest</div>
              </div>
            );
          }

          const isLocked = index > activeIndex;
          const isActive = index === activeIndex;
          const crownLevel = user?.crown_levels?.[item.skill_id] || 0;

          return (
            <div
              key={`${item.skill_id}-${index}`}
              className={`${styles.node} ${styles[`align${alignment}`]}`}
            >
              <Link
                to={`/lesson/${item.skill_id}/0`}
                className={`${styles.skill} ${isLocked ? styles.locked : ""} ${isActive ? styles.active : ""}`}
              >
                <span className={styles.skillEmoji}>{item.emoji || "⭐"}</span>
                <span className={styles.skillTitle}>{item.title}</span>
                <span className={styles.crown}>{crownLevel > 0 ? `Crown ${crownLevel}` : "New"}</span>
                {isLocked && <span className={styles.lock}>🔒</span>}
              </Link>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default PathMap;

