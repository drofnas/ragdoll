import type { ReactNode } from "react";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppProviders } from "../../../app/providers";
import { AUTH_ACCESS_TOKEN_STORAGE_KEY } from "../../../shared/state/authSession";
import {
  documentListResponse,
  jsonResponse,
  pinnedFactDetail,
  spaceListResponse,
  usageSummary,
  userProfile
} from "../../../test/testData";
import { DashboardPage } from "../pages/DashboardPage";

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
    useSpaceScope: () => ({
      activeSpace: defaultSpace,
      allSpaces: false,
      archivedSpaces: [],
      buildReadScopeParams: () => ({ space_id: defaultSpace.id }),
      isReady: true,
      refreshSpaces: async () => [defaultSpace],
      requireConcreteSpace: () => defaultSpace,
      setActiveSpace: vi.fn(),
      setAllSpaces: vi.fn(),
      spaces: [defaultSpace]
    })
  };
});

function renderDashboard() {
  render(
    <MemoryRouter initialEntries={["/dashboard"]}>
      <AppProviders>
        <Routes>
          <Route path="/dashboard" element={<DashboardPage />} />
        </Routes>
      </AppProviders>
    </MemoryRouter>
  );
}

describe("Dashboard page", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("sorts pinned facts by updated_at descending", async () => {
    window.localStorage.setItem(AUTH_ACCESS_TOKEN_STORAGE_KEY, "token");

    const newerFact = {
      ...pinnedFactDetail,
      id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
      title: "API runtime",
      updated_at: "2026-06-24T10:00:00Z"
    };

    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        const requestUrl = new URL(url, "http://localhost");
        if (url.includes("/api/v1/auth/me")) {
          return jsonResponse(userProfile);
        }
        if (url.includes("/api/v1/spaces")) {
          return jsonResponse(spaceListResponse);
        }
        if (url.includes("/api/v1/documents")) {
          return jsonResponse(documentListResponse);
        }
        if (url.includes("/api/v1/usage/me")) {
          return jsonResponse(usageSummary);
        }
        if (url.includes("/api/v1/pinned-facts")) {
          expect(requestUrl.searchParams.get("sort_key")).toBe("updated_at");
          expect(requestUrl.searchParams.get("descending")).toBe("true");
          return jsonResponse({
            items: [newerFact, pinnedFactDetail],
            page: 1,
            page_size: 5,
            total: 2
          });
        }
        return jsonResponse({}, { status: 404 });
      })
    );

    renderDashboard();

    await screen.findByText("API runtime");
    expect(screen.getByText("Current backend framework")).toBeInTheDocument();
  });
});
