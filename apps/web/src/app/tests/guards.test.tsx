import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";

import { AppProviders } from "../providers";
import { AdminRoute } from "../guards/AdminRoute";
import { ProtectedRoute } from "../guards/ProtectedRoute";

function renderProtected(path: string, mode?: "anonymous" | "user" | "admin") {
  globalThis.__RAGDOLL_SCAFFOLD_AUTH_MODE__ = mode;
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
  beforeEach(() => {
    globalThis.__RAGDOLL_SCAFFOLD_AUTH_MODE__ = undefined;
  });

  it("redirects anonymous users away from protected routes", () => {
    renderProtected("/protected", "anonymous");
    expect(screen.getByText("login-page")).toBeInTheDocument();
  });

  it("redirects non-admin users away from admin routes", () => {
    renderProtected("/admin", "user");
    expect(screen.getByText("dashboard-page")).toBeInTheDocument();
  });

  it("allows admin scaffold mode through admin route", () => {
    renderProtected("/admin", "admin");
    expect(screen.getByText("admin-page")).toBeInTheDocument();
  });
});
