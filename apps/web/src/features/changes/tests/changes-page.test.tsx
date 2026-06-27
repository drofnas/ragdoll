import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppProviders } from "../../../app/providers";
import { AUTH_ACCESS_TOKEN_STORAGE_KEY } from "../../../shared/state/authSession";
import {
  changeDetail,
  changeListResponse,
  correctionDetail,
  correctionListResponse,
  jsonResponse,
  spaceListResponse,
  userProfile
} from "../../../test/testData";
import { ChangesPage } from "../pages/ChangesPage";

function renderChangesPage(initialEntry: string) {
  render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <AppProviders>
        <Routes>
          <Route path="/changes" element={<ChangesPage />} />
        </Routes>
      </AppProviders>
    </MemoryRouter>
  );
}

describe("ChangesPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("loads change detail on first expand, keeps it cached, and marks the item as read without refetching detail", async () => {
    window.localStorage.setItem(AUTH_ACCESS_TOKEN_STORAGE_KEY, "token");

    let currentDetail = changeDetail;
    let currentList = changeListResponse;
    let changeDetailRequests = 0;

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
        if (url.includes(`/api/v1/changes/${changeDetail.id}/read`)) {
          currentDetail = { ...currentDetail, is_read: true };
          currentList = {
            ...currentList,
            items: currentList.items.map((item) =>
              item.id === changeDetail.id ? { ...item, is_read: true } : item
            )
          };
          return jsonResponse({
            change_event_id: changeDetail.id,
            read_at: "2026-06-22T17:18:00Z"
          });
        }
        if (url.includes(`/api/v1/changes/${changeDetail.id}`)) {
          changeDetailRequests += 1;
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

    renderChangesPage("/changes");

    const user = userEvent.setup();
    const trigger = await screen.findByRole("button", {
      name: new RegExp(changeListResponse.items[0].title, "i")
    });

    expect(changeDetailRequests).toBe(0);

    await user.click(trigger);
    await screen.findByRole("button", { name: "Mark read" });
    expect(changeDetailRequests).toBe(1);
    expect(screen.getByTestId(`change-detail-card-${changeDetail.id}`)).toHaveClass(
      "rounded-md",
      "border",
      "border-border",
      "bg-white",
      "p-4"
    );

    await user.click(trigger);
    await waitFor(() => expect(trigger).toHaveAttribute("aria-expanded", "false"));
    expect(screen.queryByRole("button", { name: "Mark read" })).not.toBeInTheDocument();
    expect(screen.queryByText("Change detail")).not.toBeInTheDocument();
    expect(screen.queryByTestId(`change-detail-card-${changeDetail.id}`)).not.toBeInTheDocument();

    await user.click(trigger);
    await waitFor(() => expect(trigger).toHaveAttribute("aria-expanded", "true"));
    await screen.findByRole("button", { name: "Mark read" });
    expect(changeDetailRequests).toBe(1);

    await user.click(screen.getByRole("button", { name: "Mark read" }));

    await waitFor(() =>
      expect(screen.getByText("Change marked as read.")).toBeInTheDocument()
    );
    await waitFor(() => expect(screen.getAllByText("read").length).toBeGreaterThan(0));
    expect(changeDetailRequests).toBe(1);
  });

  it("opens the selected change accordion from the deep link query param", async () => {
    window.localStorage.setItem(AUTH_ACCESS_TOKEN_STORAGE_KEY, "token");

    let changeDetailRequests = 0;

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
        if (url.includes(`/api/v1/changes/${changeDetail.id}`)) {
          changeDetailRequests += 1;
          return jsonResponse(changeDetail);
        }
        if (url.includes("/api/v1/changes")) {
          return jsonResponse(changeListResponse);
        }
        if (url.includes("/api/v1/corrections")) {
          return jsonResponse(correctionListResponse);
        }
        return jsonResponse({}, { status: 404 });
      })
    );

    renderChangesPage(`/changes?change_id=${changeDetail.id}`);

    await screen.findByRole("button", { name: "Mark read" });
    expect(changeDetailRequests).toBe(1);
  });

  it.each([
    ["verify", "verified", "Correction verified."],
    ["reject", "rejected", "Correction rejected."]
  ] as const)(
    "opens the deep-linked correction accordion, reuses cached detail, and %ss without refetching detail",
    async (action, expectedStatus, expectedMessage) => {
      window.localStorage.setItem(AUTH_ACCESS_TOKEN_STORAGE_KEY, "token");

      let correctionDetailRequests = 0;
      let currentCorrection = correctionDetail;

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
          if (url.includes(`/api/v1/corrections/${correctionDetail.id}/${action}`)) {
            currentCorrection = { ...currentCorrection, status: expectedStatus };
            return jsonResponse(currentCorrection);
          }
          if (url.includes(`/api/v1/corrections/${correctionDetail.id}`)) {
            correctionDetailRequests += 1;
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

      renderChangesPage(
        `/changes?tab=corrections&correction_id=${correctionDetail.id}&status=pending`
      );

      const user = userEvent.setup();
      const trigger = await screen.findByRole("button", {
        name: new RegExp(correctionDetail.proposed_value, "i")
      });

      await screen.findByLabelText(/Review notes/i);
      expect(correctionDetailRequests).toBe(1);
      expect(
        screen.getByTestId(`correction-detail-card-${correctionDetail.id}`)
      ).toHaveClass("rounded-md", "border", "border-border", "bg-white", "p-4");

      await user.click(trigger);
      await waitFor(() => expect(trigger).toHaveAttribute("aria-expanded", "false"));
      expect(screen.queryByLabelText(/Review notes/i)).not.toBeInTheDocument();
      expect(screen.queryByText("Correction detail")).not.toBeInTheDocument();
      expect(
        screen.queryByTestId(`correction-detail-card-${correctionDetail.id}`)
      ).not.toBeInTheDocument();

      await user.click(trigger);
      await waitFor(() => expect(trigger).toHaveAttribute("aria-expanded", "true"));
      await screen.findByLabelText(/Review notes/i);
      expect(correctionDetailRequests).toBe(1);

      await user.type(screen.getByLabelText(/Review notes/i), "Looks correct.");
      await user.click(
        screen.getByRole("button", { name: action === "verify" ? "Verify" : "Reject" })
      );

      await waitFor(() => expect(screen.getByText(expectedMessage)).toBeInTheDocument());
      await waitFor(() => expect(screen.getAllByText(expectedStatus).length).toBeGreaterThan(0));
      expect(correctionDetailRequests).toBe(1);
    }
  );
});
