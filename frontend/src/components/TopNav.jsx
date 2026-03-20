import React, { useMemo, useState } from "react";
import { getTargetFlag } from "../utils/uiStrings.js";
import ShopModal from "./ShopModal.jsx";
import styles from "./TopNav.module.css";

const TopNav = ({ user, ui, notifications, onReadAll }) => {
  const [open, setOpen] = useState(false);
  const [shopOpen, setShopOpen] = useState(false);
  const flag = useMemo(() => getTargetFlag(user?.target_language), [user?.target_language]);
  const level = user?.cefr_level || user?.enrolled_languages?.[0]?.cefr_level || "A1";
  const gems = user?.gems ?? 0;
  const hearts = user?.hearts ?? 5;
  const streak = user?.streak ?? 0;
  const unread = notifications.filter((item) => !item.read).length;

  return (
    <>
      <div className={styles.topNav}>
        <div className={styles.left}>
          <div className={styles.statPill}>
            <span className={styles.statIcon}>{"\u{1F525}"}</span>
            <div>
              <div className={styles.statLabel}>{ui.streak}</div>
              <div className={styles.statValue}>{streak}</div>
            </div>
          </div>
        </div>
        <div className={styles.center}>
          <span className={styles.flag}>{flag}</span>
          <span className={styles.level}>{level}</span>
        </div>
        <div className={styles.right}>
          <button type="button" className={styles.statPill} onClick={() => setShopOpen(true)} aria-label="Open gem shop">
            <span className={styles.statIcon}>{"\u{1F48E}"}</span>
            <div>
              <div className={styles.statLabel}>{ui.gems}</div>
              <div className={styles.statValue}>{gems}</div>
            </div>
          </button>
          <div className={styles.statPill}>
            <span className={styles.statIcon}>{"\u{2764}\u{FE0F}"}</span>
            <div>
              <div className={styles.statLabel}>{ui.hearts}</div>
              <div className={styles.statValue}>{hearts}</div>
            </div>
          </div>
          <button className={styles.bell} onClick={() => setOpen((prev) => !prev)} type="button" aria-label="Notifications">
            <span className={styles.bellIcon}>{"\u{1F514}"}</span>
            {unread > 0 && <span className={styles.badge}>{unread}</span>}
          </button>
        </div>
        {open && (
          <div className={styles.panel}>
            <div className={styles.panelHeader}>
              <span>{ui.notifications}</span>
              <button className={styles.panelButton} onClick={onReadAll} type="button">
                Mark all read
              </button>
            </div>
            <div className={styles.panelList}>
              {notifications.length === 0 && <div className={styles.panelEmpty}>No notifications yet.</div>}
              {notifications.map((item) => (
                <div key={item._id || item.id} className={`${styles.panelItem} ${item.read ? styles.read : ""}`}>
                  <div className={styles.panelTitle}>{item.title || "Update"}</div>
                  <div className={styles.panelBody}>{item.body || item.message}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
      {shopOpen && <ShopModal onClose={() => setShopOpen(false)} onUpdate={() => window.location.reload()} />}
    </>
  );
};

export default TopNav;
