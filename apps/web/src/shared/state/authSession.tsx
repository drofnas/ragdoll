import type { LoginTokenResponse, UserProfileResponse } from "@contracts";
import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type PropsWithChildren
} from "react";
import { useQueryClient } from "@tanstack/react-query";

import { ApiProblemError, apiClient, configureApiClientAuth } from "../api/client";

export type AuthSessionStatus = "anonymous" | "authenticated" | "loading" | "unavailable";

export const AUTH_ACCESS_TOKEN_STORAGE_KEY = "ragdoll.auth.accessToken";

interface LoginCredentials {
  password: string;
  username: string;
}

interface AuthSessionContextValue {
  currentUser: UserProfileResponse | null;
  isAdmin: boolean;
  isAuthenticated: boolean;
  login: (credentials: LoginCredentials) => Promise<UserProfileResponse>;
  logout: () => void;
  refreshSession: () => Promise<UserProfileResponse | null>;
  sessionErrorMessage: string | null;
  status: AuthSessionStatus;
}

const AuthSessionContext = createContext<AuthSessionContextValue | null>(null);

function readStoredToken() {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(AUTH_ACCESS_TOKEN_STORAGE_KEY);
}

function writeStoredToken(token: string | null) {
  if (typeof window === "undefined") {
    return;
  }
  if (token) {
    window.localStorage.setItem(AUTH_ACCESS_TOKEN_STORAGE_KEY, token);
    return;
  }
  window.localStorage.removeItem(AUTH_ACCESS_TOKEN_STORAGE_KEY);
}

async function fetchCurrentUser() {
  return apiClient.getJson<UserProfileResponse>("/api/v1/auth/me");
}

export function AuthSessionProvider({ children }: PropsWithChildren) {
  const queryClient = useQueryClient();
  const tokenRef = useRef<string | null>(readStoredToken());
  const logoutRef = useRef<() => void>(() => undefined);
  const [status, setStatus] = useState<AuthSessionStatus>(tokenRef.current ? "loading" : "anonymous");
  const [currentUser, setCurrentUser] = useState<UserProfileResponse | null>(null);
  const [sessionErrorMessage, setSessionErrorMessage] = useState<string | null>(null);

  function clearCachedProductState() {
    queryClient.clear();
  }

  function applyAuthenticatedUser(user: UserProfileResponse) {
    setCurrentUser(user);
    setSessionErrorMessage(null);
    setStatus("authenticated");
    return user;
  }

  function applyAnonymousState() {
    tokenRef.current = null;
    writeStoredToken(null);
    setCurrentUser(null);
    setSessionErrorMessage(null);
    setStatus("anonymous");
    clearCachedProductState();
  }

  function applyUnavailableState(error: unknown) {
    if (error instanceof ApiProblemError) {
      setSessionErrorMessage(error.problem.detail);
    } else {
      setSessionErrorMessage(
        "The backend could not be reached. Your saved session is still on this device."
      );
    }
    setStatus("unavailable");
  }

  async function refreshSession() {
    const accessToken = tokenRef.current;
    if (!accessToken) {
      applyAnonymousState();
      return null;
    }

    setStatus("loading");
    try {
      const user = await fetchCurrentUser();
      return applyAuthenticatedUser(user);
    } catch (error) {
      if (error instanceof ApiProblemError && error.status === 401) {
        applyAnonymousState();
        return null;
      }
      applyUnavailableState(error);
      throw error;
    }
  }

  function logout() {
    applyAnonymousState();
  }

  async function login(credentials: LoginCredentials) {
    const token = await apiClient.postForm<LoginTokenResponse>("/api/v1/auth/login", credentials, {
      auth: false
    });
    tokenRef.current = token.access_token;
    writeStoredToken(token.access_token);
    const user = await fetchCurrentUser();
    return applyAuthenticatedUser(user);
  }

  useEffect(() => {
    logoutRef.current = logout;
  });

  useEffect(() => {
    configureApiClientAuth({
      getAccessToken: () => tokenRef.current,
      onUnauthorized: () => logoutRef.current()
    });
  }, []);

  useEffect(() => {
    if (!tokenRef.current) {
      return;
    }
    void refreshSession().catch(() => undefined);
  }, []);

  const value: AuthSessionContextValue = {
    currentUser,
    isAdmin: currentUser?.is_admin === true,
    isAuthenticated: currentUser !== null,
    login,
    logout,
    refreshSession,
    sessionErrorMessage,
    status
  };

  return <AuthSessionContext.Provider value={value}>{children}</AuthSessionContext.Provider>;
}

export function useAuthSession() {
  const context = useContext(AuthSessionContext);
  if (context == null) {
    throw new Error("useAuthSession must be used inside AuthSessionProvider");
  }
  return context;
}
