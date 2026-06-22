import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppProviders } from "../../../app/providers";
import { AUTH_ACCESS_TOKEN_STORAGE_KEY } from "../../../shared/state/authSession";
import { AccountPage } from "../pages/AccountPage";
import { jsonResponse, spaceListResponse, usageSummary, userProfile } from "../../../test/testData";

describe("AccountPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("loads usage and saves profile updates", async () => {
    window.localStorage.setItem(AUTH_ACCESS_TOKEN_STORAGE_KEY, "token");

    let currentUser = { ...userProfile };
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.includes("/api/v1/auth/me") && (!init?.method || init.method === "GET")) {
          return jsonResponse(currentUser);
        }
        if (url.includes("/api/v1/spaces")) {
          return jsonResponse(spaceListResponse);
        }
        if (url.includes("/api/v1/usage/me")) {
          return jsonResponse(usageSummary);
        }
        if (url.includes("/api/v1/auth/me") && init?.method === "PATCH") {
          currentUser = {
            ...currentUser,
            full_name: "Updated User"
          };
          return jsonResponse(currentUser);
        }
        return jsonResponse({}, { status: 404 });
      })
    );

    render(
      <MemoryRouter>
        <AppProviders>
          <AccountPage />
        </AppProviders>
      </MemoryRouter>
    );

    const user = userEvent.setup();
    await waitFor(() => expect(screen.getByText("Usage summary")).toBeInTheDocument());

    const fullNameInput = screen.getByLabelText("Full name");
    await user.clear(fullNameInput);
    await user.type(fullNameInput, "Updated User");
    await user.click(screen.getByRole("button", { name: "Save account changes" }));

    await waitFor(() => expect(screen.getByText("Profile updated.")).toBeInTheDocument());
  });
});
