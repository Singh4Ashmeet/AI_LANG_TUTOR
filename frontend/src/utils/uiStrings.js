const base = {
  learn: "Learn",
  tutor: "Tutor",
  league: "League",
  practice: "Practice",
  profile: "Profile",
  streak: "Streak",
  gems: "Gems",
  hearts: "Hearts",
  notifications: "Notifications"
};

const translations = {
  spanish: {
    learn: "Aprender",
    tutor: "Tutor",
    league: "Liga",
    practice: "Practicar",
    profile: "Perfil",
    streak: "Racha",
    gems: "Gemas",
    hearts: "Vidas",
    notifications: "Notificaciones"
  },
  french: {
    learn: "Apprendre",
    tutor: "Tuteur",
    league: "Ligue",
    practice: "Pratique",
    profile: "Profil",
    streak: "Série",
    gems: "Gemmes",
    hearts: "Vies",
    notifications: "Notifications"
  },
  german: {
    learn: "Lernen",
    tutor: "Tutor",
    league: "Liga",
    practice: "Üben",
    profile: "Profil",
    streak: "Serie",
    gems: "Edelsteine",
    hearts: "Leben",
    notifications: "Benachrichtigungen"
  },
  italian: {
    learn: "Impara",
    tutor: "Tutor",
    league: "Lega",
    practice: "Pratica",
    profile: "Profilo",
    streak: "Serie",
    gems: "Gemme",
    hearts: "Vite",
    notifications: "Notifiche"
  },
  portuguese: {
    learn: "Aprender",
    tutor: "Tutor",
    league: "Liga",
    practice: "Praticar",
    profile: "Perfil",
    streak: "Sequência",
    gems: "Gemas",
    hearts: "Vidas",
    notifications: "Notificações"
  },
  japanese: {
    learn: "学ぶ",
    tutor: "チューター",
    league: "リーグ",
    practice: "練習",
    profile: "プロフィール",
    streak: "連続",
    gems: "ジェム",
    hearts: "ハート",
    notifications: "通知"
  },
  korean: {
    learn: "학습",
    tutor: "튜터",
    league: "리그",
    practice: "연습",
    profile: "프로필",
    streak: "연속",
    gems: "젬",
    hearts: "하트",
    notifications: "알림"
  }
};

export const getUiStrings = (targetLanguage, immersionMode) => {
  if (!immersionMode) return base;
  const key = (targetLanguage || "").toLowerCase();
  return translations[key] || base;
};

export const getTargetFlag = (targetLanguage) => {
  const key = (targetLanguage || "").toLowerCase();
  const flags = {
    spanish: "🇪🇸",
    french: "🇫🇷",
    german: "🇩🇪",
    italian: "🇮🇹",
    portuguese: "🇵🇹",
    japanese: "🇯🇵",
    korean: "🇰🇷",
    chinese: "🇨🇳",
    english: "🇺🇸"
  };
  return flags[key] || "🌍";
};

