import React, { createContext, useContext, useEffect, useReducer } from "react";
import { api } from "../api.js";

const initialState = { user: null, isAuthenticated: false, isLoading: true };

const reducer = (state, action) => {
  switch (action.type) {
    case "LOGIN":
      return { user: action.payload, isAuthenticated: true, isLoading: false };
    case "LOGOUT":
      return { user: null, isAuthenticated: false, isLoading: false };
    case "SET_USER":
      return { ...state, user: action.payload };
    case "STOP_LOADING":
      return { ...state, isLoading: false };
    default:
      return state;
  }
};

const AuthContext = createContext(null);

const TEMP_TOKEN_KEY = "temp_token";
const OTP_DELIVERY_MODE_KEY = "otp_delivery_mode";

export const AuthProvider = ({ children }) => {
  const [state, dispatch] = useReducer(reducer, initialState);

  useEffect(() => {
    const init = async () => {
      const token = localStorage.getItem("token");
      if (!token) {
        dispatch({ type: "STOP_LOADING" });
        return;
      }
      try {
        const me = await api.get("/users/me");
        dispatch({ type: "LOGIN", payload: me });
      } catch (err) {
        localStorage.removeItem("token");
        localStorage.removeItem("refresh_token");
        dispatch({ type: "LOGOUT" });
      }
    };
    init();
  }, []);

  const login = async (email, password) => {
    const result = await api.post("/auth/login/credentials", { email, password });
    if (!result?.temp_token) {
      throw new Error("Unable to start OTP login");
    }
    localStorage.setItem(TEMP_TOKEN_KEY, result.temp_token);
    localStorage.setItem(OTP_DELIVERY_MODE_KEY, result.delivery_mode || "email");
    return result;
  };

  const resendOtp = async () => {
    const temp = localStorage.getItem(TEMP_TOKEN_KEY);
    if (!temp) throw new Error("Temporary login token missing");
    const result = await api.post("/auth/login/resend-otp", {}, { token: temp });
    localStorage.setItem(OTP_DELIVERY_MODE_KEY, result.delivery_mode || "email");
    return result;
  };

  const verifyOtp = async (code) => {
    const temp = localStorage.getItem(TEMP_TOKEN_KEY);
    if (!temp) throw new Error("Temporary login token missing");
    const result = await api.post("/auth/login/verify-otp", { code }, { token: temp });

    if (result?.totp_required && result?.temp_token) {
      localStorage.setItem(TEMP_TOKEN_KEY, result.temp_token);
      return { totpRequired: true };
    }

    localStorage.removeItem(TEMP_TOKEN_KEY);
    localStorage.removeItem(OTP_DELIVERY_MODE_KEY);
    localStorage.setItem("token", result.access_token);
    if (result.refresh_token) localStorage.setItem("refresh_token", result.refresh_token);
    dispatch({ type: "LOGIN", payload: result.user });
    return { totpRequired: false, user: result.user };
  };

  const verifyTotp = async (code) => {
    const temp = localStorage.getItem(TEMP_TOKEN_KEY);
    if (!temp) throw new Error("Temporary TOTP token missing");
    const result = await api.post("/auth/login/verify-totp", { code }, { token: temp });
    localStorage.removeItem(TEMP_TOKEN_KEY);
    localStorage.removeItem(OTP_DELIVERY_MODE_KEY);
    localStorage.setItem("token", result.access_token);
    if (result.refresh_token) localStorage.setItem("refresh_token", result.refresh_token);
    dispatch({ type: "LOGIN", payload: result.user });
    return result.user;
  };

  const refreshMe = async () => {
    const me = await api.get("/users/me");
    dispatch({ type: "SET_USER", payload: me });
    return me;
  };

  const logout = async () => {
    try {
      if (localStorage.getItem("token")) {
        await api.post("/auth/logout");
      }
    } catch (err) {
      // Ignore and force local sign out
    }
    localStorage.removeItem("token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem(TEMP_TOKEN_KEY);
    localStorage.removeItem(OTP_DELIVERY_MODE_KEY);
    dispatch({ type: "LOGOUT" });
  };

  return (
    <AuthContext.Provider
      value={{
        ...state,
        login,
        verifyOtp,
        resendOtp,
        verifyTotp,
        refreshMe,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
