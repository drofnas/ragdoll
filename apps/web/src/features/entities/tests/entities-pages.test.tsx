import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppProviders } from "../../../app/providers";
import { AUTH_ACCESS_TOKEN_STORAGE_KEY } from "../../../shared/state/authSession";
import { EntitiesPage } from "../pages/EntitiesPage";
import { EntityDetailPage } from "../pages/EntityDetailPage";
import {
  entityDetail,
  entityGraph,
  entityListResponse,
  jsonResponse,
  spaceListResponse,
  userProfile
} from "../../../test/testData";

describe("entity pages", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("loads the entity list with scope-aware filters", async () => {
    window.localStorage.setItem(AUTH_ACCESS_TOKEN_STORAGE_KEY, "token");

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
        if (url.includes("/api/v1/entities")) {
          expect(url).toContain("q=FastAPI");
          return jsonResponse(entityListResponse);
        }
        return jsonResponse({}, { status: 404 });
      })
    );

    render(
      <MemoryRouter initialEntries={["/entities?q=FastAPI"]}>
        <AppProviders>
          <Routes>
            <Route path="/entities" element={<EntitiesPage />} />
          </Routes>
        </AppProviders>
      </MemoryRouter>
    );

    await waitFor(() => expect(screen.getByRole("columnheader", { name: "Name" })).toBeInTheDocument());
    expect(screen.getByRole("columnheader", { name: "Type" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Latest Mention" })).toBeInTheDocument();
    expect(screen.getByText("FastAPI")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "View Details" })).toHaveAttribute(
      "href",
      `/entities/${entityDetail.id}`
    );
  });

  it("hydrates entity detail, provenance, history, and lightweight graph data", async () => {
    window.localStorage.setItem(AUTH_ACCESS_TOKEN_STORAGE_KEY, "token");

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
        if (url.includes(`/api/v1/entities/${entityDetail.id}`)) {
          return jsonResponse(entityDetail);
        }
        if (url.includes(`/api/v1/knowledge-graph/entities/${entityDetail.id}/subgraph`)) {
          expect(url).toContain("depth=2");
          expect(url).toContain("limit=10");
          return jsonResponse({ ...entityGraph, depth: 2 });
        }
        return jsonResponse({}, { status: 404 });
      })
    );

    render(
      <MemoryRouter initialEntries={[`/entities/${entityDetail.id}?depth=2&limit=10`]}>
        <AppProviders>
          <Routes>
            <Route path="/entities/:entityId" element={<EntityDetailPage />} />
          </Routes>
        </AppProviders>
      </MemoryRouter>
    );

    await waitFor(() => expect(screen.getByText(/depends_on/)).toBeInTheDocument());
    expect(screen.getByRole("heading", { name: "FastAPI" })).toBeInTheDocument();
    expect(screen.getByText(/OpenAPI/)).toBeInTheDocument();
    expect(screen.getByText(/depends_on/)).toBeInTheDocument();
  });
});
