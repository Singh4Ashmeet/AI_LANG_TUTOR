const base = {
  learn: "Learn",
  tutor: "Tutor",
  league: "League",
  practice: "Practice",
  profile: "Profile",
  streak: "Streak",
  gems: "Gems",
  hearts: "Hearts",
  notifications: "Notifications",
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
    notifications: "Notificaciones",
  },
  french: {
    learn: "Apprendre",
    tutor: "Tuteur",
    league: "Ligue",
    practice: "Pratique",
    profile: "Profil",
    streak: "Serie",
    gems: "Gemmes",
    hearts: "Vies",
    notifications: "Notifications",
  },
  german: {
    learn: "Lernen",
    tutor: "Tutor",
    league: "Liga",
    practice: "Uben",
    profile: "Profil",
    streak: "Serie",
    gems: "Edelsteine",
    hearts: "Leben",
    notifications: "Benachrichtigungen",
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
    notifications: "Notifiche",
  },
  portuguese: {
    learn: "Aprender",
    tutor: "Tutor",
    league: "Liga",
    practice: "Praticar",
    profile: "Perfil",
    streak: "Sequencia",
    gems: "Gemas",
    hearts: "Vidas",
    notifications: "Notificacoes",
  },
  japanese: {
    learn: "Manabu",
    tutor: "Chuta",
    league: "Rigu",
    practice: "Renshu",
    profile: "Purofiru",
    streak: "Renzoku",
    gems: "Jemu",
    hearts: "Hato",
    notifications: "Tsuchi",
  },
  korean: {
    learn: "Haksub",
    tutor: "Tyuteo",
    league: "Ligeu",
    practice: "Yeonseub",
    profile: "Peuropil",
    streak: "Yeonsok",
    gems: "Jem",
    hearts: "Hateu",
    notifications: "Allim",
  },
};

export const getUiStrings = (targetLanguage, immersionMode) => {
  if (!immersionMode) return base;
  const key = (targetLanguage || "").toLowerCase();
  return translations[key] || base;
};

const FLAGS = {
  spanish: "\u{1F1EA}\u{1F1F8}",
  french: "\u{1F1EB}\u{1F1F7}",
  german: "\u{1F1E9}\u{1F1EA}",
  italian: "\u{1F1EE}\u{1F1F9}",
  portuguese: "\u{1F1F5}\u{1F1F9}",
  japanese: "\u{1F1EF}\u{1F1F5}",
  korean: "\u{1F1F0}\u{1F1F7}",
  chinese: "\u{1F1E8}\u{1F1F3}",
  english: "\u{1F1FA}\u{1F1F8}",
};

export const getTargetFlag = (targetLanguage) => FLAGS[(targetLanguage || "").toLowerCase()] || "\u{1F310}";
