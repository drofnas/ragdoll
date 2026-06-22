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

  it("renders public home route", () => {
    renderRoute("/");
    expect(screen.getByText("Ragdoll Workspace")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Status" })).toHaveAttribute(
      "href",
      "http://localhost:8031/status"
    );
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
