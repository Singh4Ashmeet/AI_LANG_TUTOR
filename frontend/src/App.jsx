import React from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import { AuthProvider, useAuth } from "./context/AuthContext";
import LoadingOverlay from "./components/LoadingOverlay";
import UserLayout from "./components/UserLayout";

// Pages
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Register from "./pages/Register";
import OtpVerify from "./pages/OtpVerify";
import TotpVerify from "./pages/TotpVerify";
import ForgotPw from "./pages/ForgotPw";
import ResetPw from "./pages/ResetPw";
import Onboarding from "./pages/Onboarding";
import Dashboard from "./pages/Dashboard";
import Lesson from "./pages/Lesson";
import LessonComplete from "./pages/LessonComplete";
import Practice from "./pages/Practice";
import Flashcards from "./pages/Flashcards";
import Listening from "./pages/Listening";
import Stories from "./pages/Stories";
import SpeedRound from "./pages/SpeedRound";
import VocabChallenge from "./pages/VocabChallenge";
import Tutor from "./pages/Tutor";
import Chat from "./pages/Chat";
import Roleplay from "./pages/Roleplay";
import Leaderboard from "./pages/Leaderboard";
import Achievements from "./pages/Achievements";
import Challenges from "./pages/Challenges";
import Journal from "./pages/Journal";
import JournalNew from "./pages/JournalNew";
import History from "./pages/History";
import SessionDetail from "./pages/SessionDetail";
import Profile from "./pages/Profile";
import Settings from "./pages/Settings";
import GrammarGuide from "./pages/GrammarGuide";
import PronunciationStudio from "./pages/PronunciationStudio";
import Friends from "./pages/Friends";
import Reading from "./pages/Reading";
import PodcastMode from "./pages/PodcastMode";
import CultureNotes from "./pages/CultureNotes";

// Admin
import AdminLayout from "./pages/admin/AdminLayout";
import AdminLogin from "./pages/admin/AdminLogin";
import AdminDashboard from "./pages/admin/AdminDashboard";
import AdminUsers from "./pages/admin/AdminUsers";
import AdminUserDetail from "./pages/admin/AdminUserDetail";
import AdminSessions from "./pages/admin/AdminSessions";
import AdminLogs from "./pages/admin/AdminLogs";
import AdminCurriculum from "./pages/admin/AdminCurriculum";
import AdminLeaderboard from "./pages/admin/AdminLeaderboard";
import AdminSystem from "./pages/admin/AdminSystem";

const Protected = ({ children, adminOnly = false }) => {
  const { user, isAuthenticated, isLoading } = useAuth();
  if (isLoading) return null;
  if (!isAuthenticated) return <Navigate to={adminOnly ? "/admin/login" : "/login"} />;
  if (adminOnly && user?.role !== "admin") return <Navigate to="/dashboard" />;
  if (!adminOnly && !user?.onboarding_complete && window.location.pathname !== "/onboarding") {
      return <Navigate to="/onboarding" />;
  }
  return children;
};

const AppRoutes = () => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) return <LoadingOverlay />;

  return (
    <Routes>
      {/* Public */}
      <Route path="/" element={isAuthenticated ? <Navigate to="/dashboard" /> : <Landing />} />
      <Route path="/login" element={isAuthenticated ? <Navigate to="/dashboard" /> : <Login />} />
      <Route path="/login/otp" element={<OtpVerify />} />
      <Route path="/login/totp" element={<TotpVerify />} />
      <Route path="/register" element={isAuthenticated ? <Navigate to="/dashboard" /> : <Register />} />
      <Route path="/forgot-password" element={<ForgotPw />} />
      <Route path="/reset-password" element={<ResetPw />} />

      {/* Onboarding */}
      <Route path="/onboarding" element={<Protected><Onboarding /></Protected>} />

      {/* App (UserLayout) */}
      <Route element={<Protected><UserLayout /></Protected>}>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/leaderboard" element={<Leaderboard />} />
        <Route path="/achievements" element={<Achievements />} />
        <Route path="/profile/achievements" element={<Achievements />} />
        <Route path="/challenges" element={<Challenges />} />
        <Route path="/friends" element={<Friends />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/history" element={<History />} />
        <Route path="/history/:id" element={<SessionDetail />} />
        <Route path="/journal" element={<Journal />} />
        <Route path="/journal/new" element={<JournalNew />} />
        <Route path="/practice/journal" element={<Journal />} />
        <Route path="/practice/journal/new" element={<JournalNew />} />
        <Route path="/grammar" element={<GrammarGuide />} />
        <Route path="/pronunciation" element={<PronunciationStudio />} />
        
        {/* Practice & Tools */}
        <Route path="/practice" element={<Practice />} />
        <Route path="/practice/flashcards" element={<Flashcards />} />
        <Route path="/practice/listening" element={<Listening />} />
        <Route path="/practice/stories" element={<Stories />} />
        <Route path="/practice/speed-round" element={<SpeedRound />} />
        <Route path="/practice/speed" element={<SpeedRound />} />
        <Route path="/practice/vocab-challenge" element={<VocabChallenge />} />
        <Route path="/practice/reading" element={<Reading />} />
        <Route path="/practice/podcast" element={<PodcastMode />} />
        <Route path="/practice/culture-notes" element={<CultureNotes />} />
        
        {/* Tutor & AI */}
        <Route path="/tutor" element={<Tutor />} />
        <Route path="/tutor/chat" element={<Chat />} />
        <Route path="/tutor/roleplay" element={<Roleplay />} />
        <Route path="/roleplay" element={<Roleplay />} />
      </Route>

      {/* Lessons (No Layout) */}
      <Route path="/lesson/:skill/:n" element={<Protected><Lesson /></Protected>} />
      <Route path="/lesson/:id" element={<Protected><Lesson /></Protected>} />
      <Route path="/lesson/complete" element={<Protected><LessonComplete /></Protected>} />

      {/* Admin */}
      <Route path="/admin/login" element={<AdminLogin />} />
      <Route element={<Protected adminOnly><AdminLayout /></Protected>}>
        <Route path="/admin" element={<AdminDashboard />} />
        <Route path="/admin/users" element={<AdminUsers />} />
        <Route path="/admin/users/:id" element={<AdminUserDetail />} />
        <Route path="/admin/sessions" element={<AdminSessions />} />
        <Route path="/admin/logs" element={<AdminLogs />} />
        <Route path="/admin/curriculum" element={<AdminCurriculum />} />
        <Route path="/admin/leaderboard" element={<AdminLeaderboard />} />
        <Route path="/admin/system" element={<AdminSystem />} />
      </Route>

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  );
};

export default function App() {
  return (
    <AuthProvider>
      <Router>
        <Toaster position="top-center" />
        <AppRoutes />
      </Router>
    </AuthProvider>
  );
}
