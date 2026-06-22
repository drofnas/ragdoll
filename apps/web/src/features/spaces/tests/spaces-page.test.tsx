import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppProviders } from "../../../app/providers";
import { AUTH_ACCESS_TOKEN_STORAGE_KEY } from "../../../shared/state/authSession";
import { ALL_SPACES_STORAGE_KEY } from "../../../shared/state/spaceScope";
import { SpacesPage } from "../pages/SpacesPage";
import { jsonResponse, spaces, spaceListResponse, userProfile } from "../../../test/testData";

describe("SpacesPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("creates a Space and shows the all-spaces warning when persisted", async () => {
    window.localStorage.setItem(AUTH_ACCESS_TOKEN_STORAGE_KEY, "token");
    window.localStorage.setItem(ALL_SPACES_STORAGE_KEY, "true");

    let currentSpaces = [...spaces];
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.includes("/api/v1/auth/me")) {
          return jsonResponse(userProfile);
        }
        if (url.includes("/api/v1/spaces") && (!init?.method || init.method === "GET")) {
          return jsonResponse({ items: currentSpaces });
        }
        if (url.endsWith("/api/v1/spaces") && init?.method === "POST") {
          currentSpaces = [
            ...currentSpaces,
            {
              ...spaceListResponse.items[0],
              id: "77777777-7777-7777-7777-777777777777",
              is_default: false,
              name: "New Space"
            }
          ];
          return jsonResponse(currentSpaces[currentSpaces.length - 1], { status: 201 });
        }
        if (url.includes("/api/v1/spaces/") && init?.method === "PATCH") {
          return jsonResponse(currentSpaces[0]);
        }
        return jsonResponse({}, { status: 404 });
      })
    );

    render(
      <MemoryRouter>
        <AppProviders>
          <SpacesPage />
        </AppProviders>
      </MemoryRouter>
    );

    const user = userEvent.setup();
    await waitFor(() => expect(screen.getByText("All-spaces mode is on")).toBeInTheDocument());

    await user.type(screen.getAllByLabelText(/Name/)[0], "New Space");
    await user.click(screen.getByRole("button", { name: "Create Space" }));

    await waitFor(() => expect(screen.getByText("New Space")).toBeInTheDocument());
  });
});
