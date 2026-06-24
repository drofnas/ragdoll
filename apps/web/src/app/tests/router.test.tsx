import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppProviders } from "../providers";
import { AppRouter } from "../router";
import { AUTH_ACCESS_TOKEN_STORAGE_KEY } from "../../shared/state/authSession";
import {
  documentListResponse,
  jsonResponse,
  spaceListResponse,
  usageSummary,
  userProfile
} from "../../test/testData";

function renderRoute(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppProviders>
        <AppRouter />
      </AppProviders>
    </MemoryRouter>
  );
}

describe("AppRouter", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("renders login on the default public route", () => {
    renderRoute("/");
    expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Status" })).toHaveAttribute("href", "/status");
    expect(screen.queryByRole("link", { name: "Home" })).not.toBeInTheDocument();
  });

  it("renders the public status page", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/status?type=json")) {
          return jsonResponse({
            application: {
              environment: "development",
              generated_at: "2026-06-23T17:00:00Z",
              name: "Ragdoll API",
              version: "0.1.0",
            },
            ollama: {
              catalog_reachable: true,
              configured_base_url: true,
              configured_models: [],
              detail: "ok",
              status: "healthy",
            },
            services: {
              database: { detail: "ok", status: "healthy" },
              graph: { detail: "ok", status: "healthy" },
              llm: { detail: "ok", status: "healthy" },
              queue: { detail: "ok", status: "healthy" },
              storage: { detail: "ok", status: "healthy" },
              vector: { detail: "ok", status: "healthy" },
            },
            status: "ok",
            supabase: {
              backend: "supabase",
              detail: "ok",
              services: {},
              status: "healthy",
            },
          });
        }
        return jsonResponse({}, { status: 404 });
      })
    );

    renderRoute("/status");

    await waitFor(() => expect(screen.getByRole("heading", { name: "Workspace status" })).toBeInTheDocument());
    await waitFor(() => expect(screen.getByText("Environment: development")).toBeInTheDocument());
    expect(screen.getByText("Service overview")).toBeInTheDocument();
  });

  it("shows a status error when the runtime status endpoint cannot be reached", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.reject(new TypeError("Failed to fetch")))
    );

    renderRoute("/status");

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("Unable to load runtime status")
    );
    expect(screen.getByText(/runtime status endpoint could not be reached/i)).toBeInTheDocument();
  });

  it("renders the authenticated dashboard when a session token is present", async () => {
    window.localStorage.setItem(AUTH_ACCESS_TOKEN_STORAGE_KEY, "user-token");
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
        if (url.includes("/api/v1/documents")) {
          return jsonResponse(documentListResponse);
        }
        if (url.includes("/api/v1/usage/me")) {
          return jsonResponse(usageSummary);
        }
        return jsonResponse({}, { status: 404 });
      })
    );

    renderRoute("/dashboard");
    await waitFor(() => expect(screen.getByText("Workspace dashboard")).toBeInTheDocument());
  });
});
