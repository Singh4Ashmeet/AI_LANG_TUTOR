import React from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext.jsx";
import Landing from "./pages/Landing.jsx";
import Login from "./pages/Login.jsx";
import OtpVerify from "./pages/OtpVerify.jsx";
import TotpVerify from "./pages/TotpVerify.jsx";
import Register from "./pages/Register.jsx";
import ForgotPw from "./pages/ForgotPw.jsx";
import ResetPw from "./pages/ResetPw.jsx";
import Onboarding from "./pages/Onboarding.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Chat from "./pages/Chat.jsx";
import Tutor from "./pages/Tutor.jsx";
import TutorChat from "./pages/TutorChat.jsx";
import Roleplay from "./pages/Roleplay.jsx";
import Practice from "./pages/Practice.jsx";
import Flashcards from "./pages/Flashcards.jsx";
import Stories from "./pages/Stories.jsx";
import Listening from "./pages/Listening.jsx";
import SpeedRound from "./pages/SpeedRound.jsx";
import VocabChallenge from "./pages/VocabChallenge.jsx";
import Journal from "./pages/Journal.jsx";
import JournalNew from "./pages/JournalNew.jsx";
import GrammarGuide from "./pages/GrammarGuide.jsx";
import PronunciationStudio from "./pages/PronunciationStudio.jsx";
import Leaderboard from "./pages/Leaderboard.jsx";
import Challenges from "./pages/Challenges.jsx";
import History from "./pages/History.jsx";
import SessionDetail from "./pages/SessionDetail.jsx";
import Profile from "./pages/Profile.jsx";
import Achievements from "./pages/Achievements.jsx";
import Settings from "./pages/Settings.jsx";
import Friends from "./pages/Friends.jsx";
import Lesson from "./pages/Lesson.jsx";
import LessonComplete from "./pages/LessonComplete.jsx";
import UserLayout from "./components/UserLayout.jsx";
import AdminLayout from "./pages/admin/AdminLayout.jsx";
import AdminDashboard from "./pages/admin/AdminDashboard.jsx";
import AdminUsers from "./pages/admin/AdminUsers.jsx";
import AdminUserDetail from "./pages/admin/AdminUserDetail.jsx";
import AdminSessions from "./pages/admin/AdminSessions.jsx";
import AdminLogs from "./pages/admin/AdminLogs.jsx";
import AdminSystem from "./pages/admin/AdminSystem.jsx";
import AdminCurriculum from "./pages/admin/AdminCurriculum.jsx";
import AdminLeaderboard from "./pages/admin/AdminLeaderboard.jsx";
import AdminLogin from "./pages/admin/AdminLogin.jsx";

const PublicRoute = ({ children }) => {
  const { isAuthenticated } = useAuth();
  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }
  return children;
};

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) return <div style={{ padding: 24 }}>Loading...</div>;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return children;
};

const AdminRoute = ({ children }) => {
  const { isAdmin, isLoading } = useAuth();
  if (isLoading) return <div style={{ padding: 24 }}>Loading...</div>;
  if (!isAdmin) return <Navigate to="/dashboard" replace />;
  return children;
};

const ProtectedLayout = () => (
  <ProtectedRoute>
    <UserLayout />
  </ProtectedRoute>
);

const AppRoutes = () => (
  <Routes>
    <Route
      path="/"
      element={
        <PublicRoute>
          <Landing />
        </PublicRoute>
      }
    />
    <Route
      path="/login"
      element={
        <PublicRoute>
          <Login />
        </PublicRoute>
      }
    />
    <Route
      path="/login/otp"
      element={
        <PublicRoute>
          <OtpVerify />
        </PublicRoute>
      }
    />
    <Route
      path="/login/totp"
      element={
        <PublicRoute>
          <TotpVerify />
        </PublicRoute>
      }
    />
    <Route
      path="/register"
      element={
        <PublicRoute>
          <Register />
        </PublicRoute>
      }
    />
    <Route
      path="/admin/login"
      element={
        <PublicRoute>
          <AdminLogin />
        </PublicRoute>
      }
    />
    <Route
      path="/forgot-password"
      element={
        <PublicRoute>
          <ForgotPw />
        </PublicRoute>
      }
    />
    <Route
      path="/reset-password"
      element={
        <PublicRoute>
          <ResetPw />
        </PublicRoute>
      }
    />
    <Route element={<ProtectedLayout />}>
      <Route path="/onboarding" element={<Onboarding />} />
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/lesson/:skill/:n" element={<Lesson />} />
      <Route path="/lesson/complete" element={<LessonComplete />} />
      <Route path="/chat" element={<Chat />} />
      <Route path="/tutor" element={<Tutor />} />
      <Route path="/tutor/chat" element={<TutorChat />} />
      <Route path="/roleplay" element={<Roleplay />} />
      <Route path="/practice" element={<Practice />} />
      <Route path="/practice/flashcards" element={<Flashcards />} />
      <Route path="/practice/stories" element={<Stories />} />
      <Route path="/practice/listening" element={<Listening />} />
      <Route path="/practice/speed" element={<SpeedRound />} />
      <Route path="/practice/vocab-challenge" element={<VocabChallenge />} />
      <Route path="/practice/journal" element={<Journal />} />
      <Route path="/practice/journal/new" element={<JournalNew />} />
      <Route path="/grammar" element={<GrammarGuide />} />
      <Route path="/pronunciation" element={<PronunciationStudio />} />
      <Route path="/leaderboard" element={<Leaderboard />} />
      <Route path="/challenges" element={<Challenges />} />
      <Route path="/flashcards" element={<Flashcards />} />
      <Route path="/history" element={<History />} />
      <Route path="/history/:id" element={<SessionDetail />} />
      <Route path="/profile" element={<Profile />} />
      <Route path="/profile/achievements" element={<Achievements />} />
      <Route path="/settings" element={<Settings />} />
      <Route path="/friends" element={<Friends />} />
    </Route>
    <Route
      path="/admin"
      element={
        <AdminRoute>
          <AdminLayout />
        </AdminRoute>
      }
    >
      <Route index element={<AdminDashboard />} />
      <Route path="users" element={<AdminUsers />} />
      <Route path="users/:id" element={<AdminUserDetail />} />
      <Route path="sessions" element={<AdminSessions />} />
      <Route path="curriculum" element={<AdminCurriculum />} />
      <Route path="leaderboard" element={<AdminLeaderboard />} />
      <Route path="logs" element={<AdminLogs />} />
      <Route path="system" element={<AdminSystem />} />
    </Route>
  </Routes>
);

const App = () => (
  <AuthProvider>
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  </AuthProvider>
);

export default App;
