import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api } from "../api.js";

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem("token"));
  const [isLoading, setIsLoading] = useState(true);

  const refreshUser = async () => {
    try {
      const data = await api.get("/auth/me");
      setUser(data);
    } catch (err) {
      localStorage.removeItem("token");
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      refreshUser();
    } else {
      setIsLoading(false);
    }
  }, [token]);

  const login = async (email, password) => {
    const data = await api.post("/auth/login/credentials", { email, password });
    sessionStorage.setItem("temp_token", data.temp_token);
    sessionStorage.setItem("pending_email", email);
    return data;
  };

  const verifyOtp = async (code) => {
    const tempToken = sessionStorage.getItem("temp_token");
    if (!tempToken) {
      throw new Error("Session expired. Please log in again.");
    }
    const data = await api.post(
      "/auth/login/verify-otp",
      { code },
      { token: tempToken }
    );
    if (data.totp_required) {
      sessionStorage.setItem("temp_token", data.temp_token);
      return { totpRequired: true };
    }
    localStorage.setItem("token", data.access_token);
    setToken(data.access_token);
    setUser(data.user);
    sessionStorage.removeItem("temp_token");
    return { totpRequired: false, user: data.user };
  };

  const resendOtp = async () => {
    const tempToken = sessionStorage.getItem("temp_token");
    if (!tempToken) {
      throw new Error("Session expired. Please log in again.");
    }
    return api.post("/auth/login/resend-otp", null, { token: tempToken });
  };

  const verifyTotp = async (code) => {
    const tempToken = sessionStorage.getItem("temp_token");
    if (!tempToken) {
      throw new Error("Session expired. Please log in again.");
    }
    const data = await api.post(
      "/auth/login/verify-totp",
      { code },
      { token: tempToken }
    );
    localStorage.setItem("token", data.access_token);
    setToken(data.access_token);
    setUser(data.user);
    sessionStorage.removeItem("temp_token");
    return data.user;
  };

  const setSession = (accessToken, nextUser) => {
    localStorage.setItem("token", accessToken);
    setToken(accessToken);
    setUser(nextUser || null);
  };

  const logout = () => {
    api.post("/auth/logout").catch(() => {});
    localStorage.removeItem("token");
    setToken(null);
    setUser(null);
  };

  const value = useMemo(
    () => ({
      user,
      token,
      isLoading,
      isAuthenticated: Boolean(user),
      isAdmin: user?.role === "admin",
      login,
      verifyOtp,
      verifyTotp,
      resendOtp,
      setSession,
      logout,
      refreshUser
    }),
    [user, token, isLoading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => useContext(AuthContext);
