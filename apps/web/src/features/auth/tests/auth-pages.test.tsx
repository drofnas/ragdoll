import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppProviders } from "../../../app/providers";
import { DashboardPage } from "../../dashboard/pages/DashboardPage";
import { LoginPage } from "../pages/LoginPage";
import { RegisterPage } from "../pages/RegisterPage";
import {
  documentListResponse,
  jsonResponse,
  spaceListResponse,
  usageSummary,
  userProfile
} from "../../../test/testData";

function renderAuthApp(initialEntries: string[]) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <AppProviders>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
        </Routes>
      </AppProviders>
    </MemoryRouter>
  );
}

describe("auth pages", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("logs in successfully and routes into the dashboard", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.includes("/api/v1/auth/login")) {
          expect(String(init?.body)).toContain("username=user%40example.com");
          return jsonResponse({ access_token: "token", must_change_password: false, token_type: "bearer" });
        }
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

    renderAuthApp(["/login"]);
    const user = userEvent.setup();

    await user.type(screen.getByLabelText(/Email/), "user@example.com");
    await user.type(screen.getByLabelText(/Password/), "secretpass");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => expect(screen.getByText("Workspace dashboard")).toBeInTheDocument());
  });

  it("redirects successful registration back to the login page with a success message", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/api/v1/auth/register")) {
          return jsonResponse(userProfile, { status: 201 });
        }
        return jsonResponse({}, { status: 404 });
      })
    );

    renderAuthApp(["/register"]);
    const user = userEvent.setup();

    await user.type(screen.getByLabelText(/Email/), "user@example.com");
    await user.type(screen.getByLabelText(/Password/), "secretpass");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    await waitFor(() => expect(screen.getByText("Account ready")).toBeInTheDocument());
    expect(screen.getByDisplayValue("user@example.com")).toBeInTheDocument();
  });
});
