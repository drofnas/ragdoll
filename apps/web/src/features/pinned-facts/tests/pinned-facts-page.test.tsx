import type { ReactNode } from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppProviders } from "../../../app/providers";
import { AUTH_ACCESS_TOKEN_STORAGE_KEY } from "../../../shared/state/authSession";
import { ACTIVE_SPACE_STORAGE_KEY, ALL_SPACES_STORAGE_KEY } from "../../../shared/state/spaceScope";
import {
  jsonResponse,
  pinnedFactCandidates,
  pinnedFactDetail,
  pinnedFactHistory,
  pinnedFactsListResponse,
  spaceListResponse,
  userProfile
} from "../../../test/testData";
import { PinnedFactDetailPage } from "../pages/PinnedFactDetailPage";
import { PinnedFactsPage } from "../pages/PinnedFactsPage";

vi.mock("../../../shared/state/spaceScope", async () => {
  const actual = await vi.importActual<typeof import("../../../shared/state/spaceScope")>(
    "../../../shared/state/spaceScope"
  );
  const defaultSpace = {
    id: "33333333-3333-3333-3333-333333333333",
    name: "Core Space"
  };

  return {
    ...actual,
    SpaceScopeProvider: ({ children }: { children: ReactNode }) => children,
    useSpaceScope: () => {
      const allSpaces = window.localStorage.getItem(actual.ALL_SPACES_STORAGE_KEY) === "true";
      return {
        activeSpace: allSpaces ? null : defaultSpace,
        allSpaces,
        archivedSpaces: [],
        buildReadScopeParams: () => (allSpaces ? { all_spaces: true } : { space_id: defaultSpace.id }),
        isReady: true,
        refreshSpaces: async () => [defaultSpace],
        requireConcreteSpace: () => defaultSpace,
        setActiveSpace: vi.fn(),
        setAllSpaces: vi.fn(),
        spaces: [defaultSpace]
      };
    }
  };
});

describe("PinnedFactsPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("creates a pinned fact from selected search evidence and renders the list", async () => {
    window.localStorage.setItem(AUTH_ACCESS_TOKEN_STORAGE_KEY, "token");

    let createCalled = false;

    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.includes("/api/v1/auth/me")) {
          return jsonResponse(userProfile);
        }
        if (url.includes("/api/v1/spaces")) {
          return jsonResponse(spaceListResponse);
        }
        if (url.includes("/api/v1/search")) {
          return jsonResponse({
            items: [
              {
                citations: pinnedFactDetail.evidence[0].citations,
                document: {
                  created_at: "2026-06-22T17:00:00Z",
                  file_type: "pdf",
                  id: pinnedFactDetail.source_document_id,
                  space_id: pinnedFactDetail.space_id,
                  title: "Implementation Plan"
                },
                entity: null,
                matched_modes: ["combined"],
                preview_text: pinnedFactDetail.evidence[0].quote,
                result_id: "result-1",
                result_kind: "document_chunk",
                score: 10
              }
            ],
            page: 1,
            page_size: 5,
            total: 1
          });
        }
        if (url.includes("/api/v1/pinned-facts") && init?.method === "POST") {
          createCalled = true;
          return jsonResponse(pinnedFactDetail);
        }
        if (url.includes("/api/v1/pinned-facts")) {
          return jsonResponse(pinnedFactsListResponse);
        }
        return jsonResponse({}, { status: 404 });
      })
    );

    render(
      <MemoryRouter initialEntries={["/pinned-facts"]}>
        <AppProviders>
          <Routes>
            <Route path="/pinned-facts" element={<PinnedFactsPage />} />
          </Routes>
        </AppProviders>
      </MemoryRouter>
    );

    await waitFor(() => expect(screen.getByText("Current backend framework")).toBeInTheDocument());
    expect(screen.getByText("FastAPI")).toBeInTheDocument();

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Key"), "project_color_scheme");
    await user.type(screen.getByLabelText("Title"), "Project color scheme");
    await user.type(screen.getByLabelText("Description / detection query"), "What is the project color scheme?");
    await user.type(screen.getByLabelText("Current value"), "Atlas");
    await user.type(screen.getByPlaceholderText("Search for the source evidence you want to pin"), "FastAPI");
    await user.click(screen.getByRole("button", { name: "Search" }));
    await user.click(await screen.findByRole("button", { name: "Use result" }));
    await user.click(screen.getByRole("button", { name: "Create pinned fact" }));

    await waitFor(() => expect(createCalled).toBe(true));
  });

  it("renders detail review actions and reverts from history", async () => {
    window.localStorage.setItem(AUTH_ACCESS_TOKEN_STORAGE_KEY, "token");
    window.localStorage.setItem(ACTIVE_SPACE_STORAGE_KEY, spaceListResponse.items[0].id);

    let accepted = false;
    let reverted = false;

    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.includes("/api/v1/auth/me")) {
          return jsonResponse(userProfile);
        }
        if (url.includes("/api/v1/spaces")) {
          return jsonResponse(spaceListResponse);
        }
        if (url.includes("/accept")) {
          accepted = true;
          return jsonResponse(pinnedFactDetail);
        }
        if (url.includes("/revert")) {
          reverted = true;
          return jsonResponse({ ...pinnedFactDetail, value_text: "FastAPI" });
        }
        if (url.includes("/candidates")) {
          return jsonResponse(pinnedFactCandidates);
        }
        if (url.includes("/history")) {
          return jsonResponse(pinnedFactHistory);
        }
        if (url.includes(`/api/v1/pinned-facts/${pinnedFactDetail.id}`)) {
          return jsonResponse(pinnedFactDetail);
        }
        return jsonResponse({}, { status: 404 });
      })
    );

    render(
      <MemoryRouter initialEntries={[`/pinned-facts/${pinnedFactDetail.id}`]}>
        <AppProviders>
          <Routes>
            <Route path="/pinned-facts/:factId" element={<PinnedFactDetailPage />} />
          </Routes>
        </AppProviders>
      </MemoryRouter>
    );

    const acceptButton = await screen.findByRole("button", { name: "Accept" });
    fireEvent.click(acceptButton);
    await waitFor(() => expect(accepted).toBe(true));

    const restoreButton = screen.getByRole("button", { name: "Restore this version" });
    fireEvent.click(restoreButton);
    await waitFor(() => expect(reverted).toBe(true));
  });

  it("disables pinned-fact writes while all-spaces mode is active", async () => {
    window.localStorage.setItem(AUTH_ACCESS_TOKEN_STORAGE_KEY, "token");
    window.localStorage.setItem(ALL_SPACES_STORAGE_KEY, "true");

    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/api/v1/auth/me")) {
          return jsonResponse(userProfile);
        }
        if (url.includes("/api/v1/spaces")) {
          return jsonResponse(spaceListResponse);
        }
        if (url.includes("/api/v1/pinned-facts")) {
          return jsonResponse(pinnedFactsListResponse);
        }
        return jsonResponse({}, { status: 404 });
      })
    );

    render(
      <MemoryRouter initialEntries={["/pinned-facts"]}>
        <AppProviders>
          <Routes>
            <Route path="/pinned-facts" element={<PinnedFactsPage />} />
          </Routes>
        </AppProviders>
      </MemoryRouter>
    );

    await waitFor(() =>
      expect(
        screen.getByText("Choose one active Space before creating or editing pinned facts.")
      ).toBeInTheDocument()
    );
    expect(screen.getByRole("button", { name: "Create pinned fact" })).toBeDisabled();
  });
});
