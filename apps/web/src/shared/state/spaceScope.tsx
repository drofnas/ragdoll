import type { ReadSpacesApiV1SpacesGetOperation, SpaceListResponse, SpaceResponse } from "@contracts";
import { createContext, useContext, useEffect, useState, type PropsWithChildren } from "react";

import { apiClient } from "../api/client";
import { useAuthSession } from "./authSession";

export const ACTIVE_SPACE_STORAGE_KEY = "ragdoll.scope.activeSpaceId";
export const ALL_SPACES_STORAGE_KEY = "ragdoll.scope.allSpaces";

type ReadScopeParams = Partial<ReadDocumentsScopeQuery>;

export interface ReadDocumentsScopeQuery {
  all_spaces: boolean;
  space_id: string;
}

interface SpaceScopeContextValue {
  activeSpace: SpaceResponse | null;
  allSpaces: boolean;
  archivedSpaces: SpaceResponse[];
  buildReadScopeParams: () => ReadScopeParams;
  isReady: boolean;
  refreshSpaces: () => Promise<SpaceResponse[]>;
  requireConcreteSpace: () => SpaceResponse;
  setActiveSpace: (space: SpaceResponse | null) => void;
  setAllSpaces: (value: boolean) => void;
  spaces: SpaceResponse[];
}

const SpaceScopeContext = createContext<SpaceScopeContextValue | null>(null);

type ReadSpacesQuery = ReadSpacesApiV1SpacesGetOperation["queryParams"];

function readStoredBoolean(key: string) {
  if (typeof window === "undefined") {
    return false;
  }
  return window.localStorage.getItem(key) === "true";
}

function readStoredString(key: string) {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(key);
}

function writeStoredString(key: string, value: string | null) {
  if (typeof window === "undefined") {
    return;
  }
  if (value) {
    window.localStorage.setItem(key, value);
    return;
  }
  window.localStorage.removeItem(key);
}

function writeStoredBoolean(key: string, value: boolean) {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(key, String(value));
}

function chooseActiveSpace(spaces: SpaceResponse[], activeSpaceId: string | null) {
  if (activeSpaceId) {
    const matchingSpace = spaces.find((space) => space.id === activeSpaceId);
    if (matchingSpace) {
      return matchingSpace;
    }
  }

  return spaces.find((space) => space.archived_at === null && space.is_default) ??
    spaces.find((space) => space.archived_at === null) ??
    null;
}

function applySpaceLoadFailure(setIsReady: (value: boolean) => void, setSpaces: (spaces: SpaceResponse[]) => void, setActiveSpace: (space: SpaceResponse | null) => void) {
  setSpaces([]);
  setActiveSpace(null);
  setIsReady(true);
}

async function fetchSpaces() {
  const query: ReadSpacesQuery = { include_archived: true };
  const response = await apiClient.getJson<SpaceListResponse>("/api/v1/spaces", { query });
  return response.items;
}

export function SpaceScopeProvider({ children }: PropsWithChildren) {
  const { status } = useAuthSession();
  const [isReady, setIsReady] = useState(status === "anonymous");
  const [spaces, setSpaces] = useState<SpaceResponse[]>([]);
  const [activeSpace, setActiveSpaceState] = useState<SpaceResponse | null>(null);
  const [allSpaces, setAllSpacesState] = useState(() => readStoredBoolean(ALL_SPACES_STORAGE_KEY));

  function applySpaceSelection(nextSpaces: SpaceResponse[]) {
    const nextActiveSpace = chooseActiveSpace(nextSpaces, readStoredString(ACTIVE_SPACE_STORAGE_KEY));
    setSpaces(nextSpaces);
    setActiveSpaceState(nextActiveSpace);
    writeStoredString(ACTIVE_SPACE_STORAGE_KEY, nextActiveSpace?.id ?? null);
    setIsReady(true);
    return nextSpaces;
  }

  function resetScope() {
    setSpaces([]);
    setActiveSpaceState(null);
    setAllSpacesState(false);
    setIsReady(status === "anonymous");
    writeStoredString(ACTIVE_SPACE_STORAGE_KEY, null);
    writeStoredBoolean(ALL_SPACES_STORAGE_KEY, false);
  }

  async function refreshSpaces() {
    const nextSpaces = await fetchSpaces();
    return applySpaceSelection(nextSpaces);
  }

  function setActiveSpace(space: SpaceResponse | null) {
    setActiveSpaceState(space);
    writeStoredString(ACTIVE_SPACE_STORAGE_KEY, space?.id ?? null);
    if (space) {
      setAllSpacesState(false);
      writeStoredBoolean(ALL_SPACES_STORAGE_KEY, false);
    }
  }

  function setAllSpaces(value: boolean) {
    setAllSpacesState(value);
    writeStoredBoolean(ALL_SPACES_STORAGE_KEY, value);
  }

  function buildReadScopeParams(): ReadScopeParams {
    if (allSpaces) {
      return { all_spaces: true };
    }
    if (activeSpace) {
      return { space_id: activeSpace.id };
    }
    return {};
  }

  function requireConcreteSpace() {
    if (allSpaces || activeSpace === null) {
      throw new Error("Choose one Space before performing this action.");
    }
    return activeSpace;
  }

  useEffect(() => {
    if (status === "anonymous") {
      resetScope();
      return;
    }
    if (status === "loading") {
      setIsReady(false);
      return;
    }
    void refreshSpaces().catch(() =>
      applySpaceLoadFailure(setIsReady, setSpaces, setActiveSpaceState)
    );
  }, [status]);

  const value: SpaceScopeContextValue = {
    activeSpace,
    allSpaces,
    archivedSpaces: spaces.filter((space) => space.archived_at !== null),
    buildReadScopeParams,
    isReady,
    refreshSpaces,
    requireConcreteSpace,
    setActiveSpace,
    setAllSpaces,
    spaces: spaces.filter((space) => space.archived_at === null)
  };

  return <SpaceScopeContext.Provider value={value}>{children}</SpaceScopeContext.Provider>;
}

export function useSpaceScope() {
  const context = useContext(SpaceScopeContext);
  if (context == null) {
    throw new Error("useSpaceScope must be used inside SpaceScopeProvider");
  }
  return context;
}
