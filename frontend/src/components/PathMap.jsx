import React, { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import styles from "./PathMap.module.css";

const PathMap = ({ sections, user }) => {
  const navigate = useNavigate();
  const [selectedSkill, setSelectedSkill] = useState(null);
  const { items, activeIndex } = useMemo(() => {
    const flattened = [];
    sections.forEach((section, sectionIndex) => {
      flattened.push({ sectionCard: true, section, sectionIndex });
      section.skills?.forEach((skill, skillIndex) => {
        flattened.push({ ...skill, sectionIndex, skillIndex, sectionTitle: section.title, sectionDescription: section.description });
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

  const openSkillPreview = (skill, locked) => {
    if (locked) return;
    setSelectedSkill(skill);
  };

  const startSelectedSkill = () => {
    if (!selectedSkill) return;
    navigate(`/lesson/${selectedSkill.skill_id}/0`);
  };

  return (
    <>
      <div className={styles.map}>
        <div className={styles.pathLine} />
        <div className={styles.nodes}>
          {items.map((item, index) => {
            const alignment = index % 3;
            if (item.sectionCard) {
              return (
                <div key={`section-${item.sectionIndex}`} className={`${styles.node} ${styles.sectionNode}`}>
                  <div className={styles.sectionCard}>
                    <span>{item.section.emoji || "\u{1F31F}"}</span>
                    <div>
                      <strong>{item.section.title || `Section ${item.sectionIndex + 1}`}</strong>
                      <p>{item.section.description || "Build new skills, then reinforce them with mixed review."}</p>
                    </div>
                  </div>
                </div>
              );
            }

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
              <div key={`${item.skill_id}-${index}`} className={`${styles.node} ${styles[`align${alignment}`]}`}>
                <button
                  type="button"
                  disabled={isLocked}
                  onClick={() => openSkillPreview(item, isLocked)}
                  className={`${styles.skill} ${isLocked ? styles.locked : ""} ${isActive ? styles.active : ""}`}
                >
                  <span className={styles.skillSection}>{item.sectionTitle}</span>
                  <span className={styles.skillEmoji}>{item.emoji || "\u{2B50}"}</span>
                  <span className={styles.skillTitle}>{item.title}</span>
                  <span className={styles.skillDescription}>{item.description || item.sectionDescription}</span>
                  <span className={styles.crown}>{crownLevel > 0 ? `Crown ${crownLevel}` : "New"}</span>
                  <span className={styles.skillAction}>{isLocked ? "Locked" : isActive ? "Start here" : "Practice"}</span>
                  {isLocked && <span className={styles.lock}>{"\u{1F512}"}</span>}
                </button>
              </div>
            );
          })}
        </div>
      </div>
      {selectedSkill && (
        <div className={styles.overlay} onClick={() => setSelectedSkill(null)} role="presentation">
          <div className={styles.previewCard} onClick={(event) => event.stopPropagation()} role="dialog" aria-modal="true">
            <div className={styles.previewEyebrow}>Skill preview</div>
            <div className={styles.previewHero}>
              <span className={styles.previewEmoji}>{selectedSkill.emoji || "\u{2B50}"}</span>
              <div>
                <h3>{selectedSkill.title}</h3>
                <p>{selectedSkill.description || selectedSkill.sectionDescription || "Learn a new pattern, then practice it in context."}</p>
              </div>
            </div>
            <div className={styles.previewStats}>
              <div>
                <strong>{user?.crown_levels?.[selectedSkill.skill_id] || 0}</strong>
                <span>Crown level</span>
              </div>
              <div>
                <strong>{selectedSkill.sectionTitle}</strong>
                <span>Path section</span>
              </div>
              <div>
                <strong>{selectedSkill.difficulty || "Guided"}</strong>
                <span>Lesson pace</span>
              </div>
            </div>
            <div className={styles.previewNote}>
              You will start with teaching cards, move into recognition and sentence building, and finish with a small real-world response.
            </div>
            <div className={styles.previewActions}>
              <button type="button" className={styles.previewSecondary} onClick={() => setSelectedSkill(null)}>
                Not now
              </button>
              <button type="button" className={styles.previewPrimary} onClick={startSelectedSkill}>
                Start this skill
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default PathMap;
