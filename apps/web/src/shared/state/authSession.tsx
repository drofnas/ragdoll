import { createContext, useContext, useMemo, useState, type PropsWithChildren } from "react";

import type { FeatureFlags, ScaffoldAuthMode, SessionUser } from "../types/app";

interface AuthSessionContextValue {
  scaffoldMode: ScaffoldAuthMode;
  currentUser: SessionUser | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
  setScaffoldMode: (mode: ScaffoldAuthMode) => void;
}

const AuthSessionContext = createContext<AuthSessionContextValue | null>(null);

function defaultFlags(): FeatureFlags {
  return {
    unified_search: true,
    search_graph_mode: false,
    search_chat_in_combined: false,
    knowledge_graph_visualizer: false,
    document_version_history: false
  };
}

function buildUser(mode: Exclude<ScaffoldAuthMode, "anonymous">): SessionUser {
  const isAdmin = mode === "admin";
  return {
    id: isAdmin ? "scaffold-admin" : "scaffold-user",
    email: isAdmin ? "admin@ragdoll.local" : "user@ragdoll.local",
    fullName: isAdmin ? "Scaffold Admin" : "Scaffold User",
    isAdmin,
    planTier: isAdmin ? "internal" : "free",
    featureFlags: isAdmin
      ? {
          unified_search: true,
          search_graph_mode: true,
          search_chat_in_combined: true,
          knowledge_graph_visualizer: true,
          document_version_history: true
        }
      : defaultFlags()
  };
}

export function resolveScaffoldAuthMode(): ScaffoldAuthMode {
  const globalOverride = globalThis.__RAGDOLL_SCAFFOLD_AUTH_MODE__;
  if (globalOverride === "anonymous" || globalOverride === "user" || globalOverride === "admin") {
    return globalOverride;
  }
  const envValue = import.meta.env.VITE_SCAFFOLD_AUTH_MODE;
  if (envValue === "user" || envValue === "admin") {
    return envValue;
  }
  return "anonymous";
}

export function AuthSessionProvider({ children }: PropsWithChildren) {
  const [scaffoldMode, setScaffoldMode] = useState<ScaffoldAuthMode>(resolveScaffoldAuthMode);

  const value = useMemo<AuthSessionContextValue>(() => {
    const currentUser = scaffoldMode === "anonymous" ? null : buildUser(scaffoldMode);
    return {
      scaffoldMode,
      currentUser,
      isAuthenticated: currentUser !== null,
      isAdmin: currentUser?.isAdmin === true,
      setScaffoldMode
    };
  }, [scaffoldMode]);

  return <AuthSessionContext.Provider value={value}>{children}</AuthSessionContext.Provider>;
}

export function useAuthSession() {
  const context = useContext(AuthSessionContext);
  if (context == null) {
    throw new Error("useAuthSession must be used inside AuthSessionProvider");
  }
  return context;
}
