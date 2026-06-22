import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AdminRoute } from "../guards/AdminRoute";
import { ProtectedRoute } from "../guards/ProtectedRoute";
import { AppProviders } from "../providers";
import { AUTH_ACCESS_TOKEN_STORAGE_KEY } from "../../shared/state/authSession";
import { adminProfile, jsonResponse, spaceListResponse, userProfile } from "../../test/testData";

function renderProtected(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppProviders>
        <Routes>
          <Route path="/login" element={<div>login-page</div>} />
          <Route path="/dashboard" element={<div>dashboard-page</div>} />
          <Route
            path="/protected"
            element={
              <ProtectedRoute>
                <div>protected-page</div>
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin"
            element={
              <AdminRoute>
                <div>admin-page</div>
              </AdminRoute>
            }
          />
        </Routes>
      </AppProviders>
    </MemoryRouter>
  );
}

describe("route guards", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("redirects anonymous users away from protected routes", () => {
    renderProtected("/protected");
    expect(screen.getByText("login-page")).toBeInTheDocument();
  });

  it("redirects non-admin users away from admin routes", async () => {
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
        return jsonResponse({}, { status: 404 });
      })
    );

    renderProtected("/admin");
    await waitFor(() => expect(screen.getByText("dashboard-page")).toBeInTheDocument());
  });

  it("allows admin users through the admin route", async () => {
    window.localStorage.setItem(AUTH_ACCESS_TOKEN_STORAGE_KEY, "admin-token");
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/api/v1/auth/me")) {
          return jsonResponse(adminProfile);
        }
        if (url.includes("/api/v1/spaces")) {
          return jsonResponse(spaceListResponse);
        }
        return jsonResponse({}, { status: 404 });
      })
    );

    renderProtected("/admin");
    await waitFor(() => expect(screen.getByText("admin-page")).toBeInTheDocument());
  });
});
