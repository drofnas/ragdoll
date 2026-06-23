import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppProviders } from "../../../app/providers";
import { AUTH_ACCESS_TOKEN_STORAGE_KEY } from "../../../shared/state/authSession";
import { ALL_SPACES_STORAGE_KEY } from "../../../shared/state/spaceScope";
import { TrackedStatePage } from "../pages/TrackedStatePage";
import {
  jsonResponse,
  spaceListResponse,
  trackedFieldDefinitions,
  trackedStateConflicts,
  trackedStateSummary,
  userProfile
} from "../../../test/testData";

describe("TrackedStatePage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("saves and recomputes tracked fields while rendering conflicts", async () => {
    window.localStorage.setItem(AUTH_ACCESS_TOKEN_STORAGE_KEY, "token");

    let patchCalled = false;
    let recomputeCalled = false;

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
        if (url.includes("/api/v1/tracked-state/fields/") && url.includes("/recompute")) {
          recomputeCalled = true;
          return jsonResponse(trackedStateSummary.items[0]);
        }
        if (url.includes("/api/v1/tracked-state/fields/") && init?.method === "PATCH") {
          patchCalled = true;
          return jsonResponse({
            ...trackedFieldDefinitions.items[0],
            label: "Backend framework"
          });
        }
        if (url.includes("/api/v1/tracked-state/fields")) {
          return jsonResponse(trackedFieldDefinitions);
        }
        if (url.includes("/api/v1/tracked-state/summary")) {
          return jsonResponse(trackedStateSummary);
        }
        if (url.includes("/api/v1/tracked-state/conflicts")) {
          return jsonResponse(trackedStateConflicts);
        }
        return jsonResponse({}, { status: 404 });
      })
    );

    render(
      <MemoryRouter initialEntries={["/tracked-state"]}>
        <AppProviders>
          <Routes>
            <Route path="/tracked-state" element={<TrackedStatePage />} />
          </Routes>
        </AppProviders>
      </MemoryRouter>
    );

    await waitFor(() =>
      expect(screen.getAllByText("Current backend framework").length).toBeGreaterThan(0)
    );
    expect(screen.getByText("Starlette")).toBeInTheDocument();

    const user = userEvent.setup();
    const labelInput = screen.getByDisplayValue("Current backend framework");
    await user.clear(labelInput);
    await user.type(labelInput, "Backend framework");
    await user.click(screen.getByRole("button", { name: "Save changes" }));
    await waitFor(() => expect(patchCalled).toBe(true));

    await user.click(screen.getByRole("button", { name: "Recompute" }));
    await waitFor(() => expect(recomputeCalled).toBe(true));
  }, 15000);

  it("disables tracked-state writes while all-spaces mode is active", async () => {
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
        if (url.includes("/api/v1/tracked-state/fields")) {
          return jsonResponse(trackedFieldDefinitions);
        }
        if (url.includes("/api/v1/tracked-state/summary")) {
          return jsonResponse(trackedStateSummary);
        }
        if (url.includes("/api/v1/tracked-state/conflicts")) {
          return jsonResponse(trackedStateConflicts);
        }
        return jsonResponse({}, { status: 404 });
      })
    );

    render(
      <MemoryRouter initialEntries={["/tracked-state"]}>
        <AppProviders>
          <Routes>
            <Route path="/tracked-state" element={<TrackedStatePage />} />
          </Routes>
        </AppProviders>
      </MemoryRouter>
    );

    await waitFor(() =>
      expect(
        screen.getByText("Choose one active Space before creating or editing tracked state.")
      ).toBeInTheDocument()
    );
    expect(screen.getByRole("button", { name: "Create field" })).toBeDisabled();
  });
});
