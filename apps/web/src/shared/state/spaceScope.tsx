import { createContext, useContext, useMemo, useState, type PropsWithChildren } from "react";

import type { SpaceSummary } from "../types/app";

interface SpaceScopeContextValue {
  activeSpace: SpaceSummary | null;
  allSpaces: boolean;
  setActiveSpace: (space: SpaceSummary | null) => void;
  setAllSpaces: (value: boolean) => void;
}

const SpaceScopeContext = createContext<SpaceScopeContextValue | null>(null);

export function SpaceScopeProvider({ children }: PropsWithChildren) {
  const [activeSpace, setActiveSpace] = useState<SpaceSummary | null>(null);
  const [allSpaces, setAllSpaces] = useState(false);

  const value = useMemo<SpaceScopeContextValue>(
    () => ({
      activeSpace,
      allSpaces,
      setActiveSpace,
      setAllSpaces
    }),
    [activeSpace, allSpaces]
  );

  return <SpaceScopeContext.Provider value={value}>{children}</SpaceScopeContext.Provider>;
}

export function useSpaceScope() {
  const context = useContext(SpaceScopeContext);
  if (context == null) {
    throw new Error("useSpaceScope must be used inside SpaceScopeProvider");
  }
  return context;
}
