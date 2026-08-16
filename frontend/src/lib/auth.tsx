"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { api, setTokens, clearTokens, getToken } from "./api";
import type { User, Tokens } from "./types";

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string, otp?: string) => Promise<void>;
  register: (data: RegisterData) => Promise<{ email_verification_token: string }>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

interface RegisterData {
  first_name: string;
  last_name: string;
  email: string;
  password: string;
  mobile_number?: string;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  async function refreshUser() {
    if (!getToken()) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      setUser(await api.get<User>("/auth/me"));
    } catch {
      clearTokens();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refreshUser();
  }, []);

  async function login(email: string, password: string, otp?: string) {
    const tokens = await api.post<Tokens>("/auth/login", { email, password, otp_code: otp || null });
    setTokens(tokens.access_token, tokens.refresh_token);
    await refreshUser();
  }

  async function register(data: RegisterData) {
    const res = await api.post<{ user: User; email_verification_token: string }>(
      "/auth/register",
      data
    );
    // Auto-login after registration.
    await login(data.email, data.password);
    return { email_verification_token: res.email_verification_token };
  }

  function logout() {
    clearTokens();
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
