import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { checkAuthStatus, logoutUser } from "./apis/user";

const AuthContext = createContext(null);

const unauthenticatedState = { status: "unauthenticated", user: null };

export const AuthProvider = ({ children }) => {
  const [auth, setAuth] = useState({ status: "checking", user: null });

  const refreshAuth = useCallback(async ({ showChecking = true } = {}) => {
    if (showChecking) {
      setAuth((current) => ({ ...current, status: "checking" }));
    }

    try {
      const response = await checkAuthStatus();
      if (response.data.is_authenticated) {
        setAuth({ status: "authenticated", user: response.data });
        return response.data;
      }
      setAuth(unauthenticatedState);
      return null;
    } catch (error) {
      setAuth(unauthenticatedState);
      return null;
    }
  }, []);

  useEffect(() => {
    refreshAuth();
  }, [refreshAuth]);

  const establishSession = useCallback((loginData) => {
    setAuth({ status: "authenticated", user: loginData });
  }, []);

  const clearSession = useCallback(() => {
    setAuth(unauthenticatedState);
  }, []);

  const updateUser = useCallback((updates) => {
    setAuth((current) => current.status === "authenticated"
      ? { ...current, user: { ...current.user, ...updates } }
      : current);
  }, []);

  const logout = useCallback(async () => {
    await logoutUser();
    clearSession();
  }, [clearSession]);

  const value = useMemo(() => ({
    ...auth,
    isAuthenticated: auth.status === "authenticated",
    refreshAuth,
    establishSession,
    updateUser,
    clearSession,
    logout,
  }), [auth, clearSession, establishSession, logout, refreshAuth, updateUser]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
