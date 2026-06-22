import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppProviders } from "../../../app/providers";
import { AUTH_ACCESS_TOKEN_STORAGE_KEY } from "../../../shared/state/authSession";
import { ChangesPage } from "../pages/ChangesPage";
import {
  changeDetail,
  changeListResponse,
  correctionDetail,
  correctionListResponse,
  jsonResponse,
  spaceListResponse,
  userProfile
} from "../../../test/testData";

describe("ChangesPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("marks activity items as read from the detail panel", async () => {
    window.localStorage.setItem(AUTH_ACCESS_TOKEN_STORAGE_KEY, "token");

    let currentDetail = changeDetail;
    let currentList = changeListResponse;

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
        if (url.includes(`/api/v1/changes/${changeDetail.id}/read`)) {
          currentDetail = { ...currentDetail, is_read: true };
          currentList = {
            ...currentList,
            items: [{ ...currentList.items[0], is_read: true }]
          };
          return jsonResponse({
            change_event_id: changeDetail.id,
            read_at: "2026-06-22T17:18:00Z"
          });
        }
        if (url.includes(`/api/v1/changes/${changeDetail.id}`)) {
          return jsonResponse(currentDetail);
        }
        if (url.includes("/api/v1/changes")) {
          return jsonResponse(currentList);
        }
        if (url.includes("/api/v1/corrections")) {
          return jsonResponse(correctionListResponse);
        }
        return jsonResponse({}, { status: 404 });
      })
    );

    render(
      <MemoryRouter initialEntries={[`/changes?change_id=${changeDetail.id}`]}>
        <AppProviders>
          <Routes>
            <Route path="/changes" element={<ChangesPage />} />
          </Routes>
        </AppProviders>
      </MemoryRouter>
    );

    await waitFor(() => expect(screen.getByText(changeDetail.title)).toBeInTheDocument());
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Mark read" }));

    await waitFor(() =>
      expect(screen.getByText("Change marked as read.")).toBeInTheDocument()
    );
    await waitFor(() => expect(screen.getAllByText("read").length).toBeGreaterThan(0));
  });

  it("filters corrections and verifies a correction from the review panel", async () => {
    window.localStorage.setItem(AUTH_ACCESS_TOKEN_STORAGE_KEY, "token");

    let currentCorrection = correctionDetail;

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
        if (url.includes(`/api/v1/corrections/${correctionDetail.id}/verify`)) {
          currentCorrection = { ...currentCorrection, status: "verified" };
          return jsonResponse(currentCorrection);
        }
        if (url.includes(`/api/v1/corrections/${correctionDetail.id}`)) {
          return jsonResponse(currentCorrection);
        }
        if (url.includes("/api/v1/corrections")) {
          return jsonResponse({
            ...correctionListResponse,
            items: [currentCorrection]
          });
        }
        if (url.includes("/api/v1/changes")) {
          return jsonResponse(changeListResponse);
        }
        return jsonResponse({}, { status: 404 });
      })
    );

    render(
      <MemoryRouter
        initialEntries={[
          `/changes?tab=corrections&correction_id=${correctionDetail.id}&status=pending`
        ]}
      >
        <AppProviders>
          <Routes>
            <Route path="/changes" element={<ChangesPage />} />
          </Routes>
        </AppProviders>
      </MemoryRouter>
    );

    await waitFor(() =>
      expect(screen.getByText(correctionDetail.proposed_value)).toBeInTheDocument()
    );

    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/Review notes/), "Looks correct.");
    await user.click(screen.getByRole("button", { name: "Verify" }));

    await waitFor(() => expect(screen.getByText("Correction verified.")).toBeInTheDocument());
    await waitFor(() => expect(screen.getAllByText("verified").length).toBeGreaterThan(0));
  });
});
