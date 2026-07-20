"use client";

import { useQueryClient } from "@tanstack/react-query";
import { createContext, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";

import * as authApi from "@/lib/api-client/auth";
import type {
  LoginRequest,
  RegisterRequest,
  UserResponse,
} from "@/lib/api-client/auth";

interface AuthContextValue {
  user: UserResponse | null;
  isLoading: boolean;
  login: (values: LoginRequest) => Promise<UserResponse>;
  register: (values: RegisterRequest) => Promise<UserResponse>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const queryClient = useQueryClient();

  useEffect(() => {
    let cancelled = false;

    void (async () => {
      const restored = await authApi.refreshSession();
      if (!restored) {
        if (!cancelled) setIsLoading(false);
        return;
      }
      try {
        const currentUser = await authApi.getCurrentUser();
        if (!cancelled) setUser(currentUser);
      } catch {
        authApi.logout();
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const login = async (values: LoginRequest) => {
    const response = await authApi.login(values);
    setUser(response.user);
    return response.user;
  };

  const register = async (values: RegisterRequest) => {
    const response = await authApi.register(values);
    setUser(response.user);
    return response.user;
  };

  const logout = () => {
    authApi.logout();
    setUser(null);
    queryClient.clear();
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
