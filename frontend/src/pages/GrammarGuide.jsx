import React, { useEffect, useMemo, useState } from "react";
import { api } from "../api.js";
import styles from "./GrammarGuide.module.css";

const normalizeSections = (guide) => {
  if (!guide) return [];
  if (Array.isArray(guide.sections)) return guide.sections;

  return Object.entries(guide)
    .filter(([, value]) => Array.isArray(value))
    .map(([category, rules]) => ({ category, rules }));
};

const GrammarGuide = () => {
  const [guide, setGuide] = useState(null);
  const [activeRule, setActiveRule] = useState(null);
  const [deepDive, setDeepDive] = useState(null);
  const [answers, setAnswers] = useState({});

  useEffect(() => {
    api.get("/grammar/guide").then(setGuide).catch(() => {});
  }, []);

  const sections = useMemo(() => normalizeSections(guide), [guide]);

  const loadDeepDive = async (rule) => {
    setActiveRule(rule);
    setAnswers({});
    const data = await api.post(`/grammar/deep-dive/${encodeURIComponent(rule)}`);
    setDeepDive(data);
  };

  const isCorrect = (exercise, answer) => {
    if (!answer) return false;
    return String(answer).trim().toLowerCase() === String(exercise.correct_answer || "").trim().toLowerCase();
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <div className={styles.eyebrow}>Grammar deep dive</div>
          <h2>Study like a guidebook, practice like a lesson</h2>
          <p>Read clear rules, scan examples, and open focused practice sets when one pattern needs extra attention.</p>
        </div>
        <div className={styles.badge}>{guide?.title || "Grammar Guide"}</div>
      </header>

      <div className={styles.layout}>
        <section className={styles.guideSection}>
          {sections.map((section) => (
            <article key={section.category} className={styles.sectionCard}>
              <div className={styles.sectionHead}>
                <span>{section.category}</span>
              </div>
              <div className={styles.rules}>
                {(section.rules || []).map((rule, index) => {
                  const ruleName = rule.rule || rule.title || `${section.category} ${index + 1}`;
                  return (
                    <div key={ruleName} className={styles.ruleCard}>
                      <div className={styles.ruleHeader}>
                        <div>
                          <h3>{ruleName}</h3>
                          <p>{rule.explanation}</p>
                        </div>
                        <button type="button" onClick={() => loadDeepDive(ruleName)}>
                          Practice this
                        </button>
                      </div>
                      <div className={styles.examples}>
                        {(rule.examples || []).map((example, exampleIndex) => (
                          <div key={`${ruleName}-${exampleIndex}`} className={styles.example}>
                            <strong>{example.target || example[0]}</strong>
                            <span>{example.native || example[1]}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            </article>
          ))}
        </section>

        <aside className={styles.practicePanel}>
          <div className={styles.practiceCard}>
            <div className={styles.practiceEyebrow}>Focused practice</div>
            <h3>{activeRule || "Pick a rule to practice"}</h3>
            {!deepDive ? (
              <p className={styles.placeholder}>Choose a rule on the left and we’ll generate a 5-question targeted review set.</p>
            ) : (
              <div className={styles.exerciseList}>
                {(deepDive.exercises || []).map((exercise, index) => (
                  <div key={`${activeRule}-${index}`} className={styles.exerciseCard}>
                    <div className={styles.exercisePrompt}>{exercise.prompt || exercise.content}</div>
                    {Array.isArray(exercise.choices) && exercise.choices.length > 0 ? (
                      <div className={styles.choiceList}>
                        {exercise.choices.map((choice) => (
                          <button
                            type="button"
                            key={choice}
                            className={`${styles.choice} ${answers[index] === choice ? styles.choiceActive : ""}`}
                            onClick={() => setAnswers((prev) => ({ ...prev, [index]: choice }))}
                          >
                            {typeof choice === "object" ? JSON.stringify(choice) : choice}
                          </button>
                        ))}
                      </div>
                    ) : (
                      <input
                        value={answers[index] || ""}
                        onChange={(event) => setAnswers((prev) => ({ ...prev, [index]: event.target.value }))}
                        placeholder="Type your answer"
                      />
                    )}
                    {answers[index] && (
                      <div className={isCorrect(exercise, answers[index]) ? styles.correct : styles.explanation}>
                        {isCorrect(exercise, answers[index])
                          ? "Correct"
                          : `Suggested answer: ${exercise.correct_answer}`}
                      </div>
                    )}
                    <div className={styles.explanation}>{exercise.explanation}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
};

export default GrammarGuide;
