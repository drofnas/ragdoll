import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppProviders } from "../../../app/providers";
import { AUTH_ACCESS_TOKEN_STORAGE_KEY } from "../../../shared/state/authSession";
import { ChatPage } from "../pages/ChatPage";
import {
  chatSessionDetail,
  chatSessionListResponse,
  correctionDetail,
  jsonResponse,
  spaceListResponse,
  userProfile
} from "../../../test/testData";

describe("ChatPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it(
    "renders an assistant answer and submits a correction from the transcript",
    async () => {
      window.localStorage.setItem(AUTH_ACCESS_TOKEN_STORAGE_KEY, "token");
      vi.spyOn(Date, "now").mockReturnValue(new Date("2026-06-22T17:25:00Z").getTime());

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
          if (url.includes("/api/v1/chat/sessions/") && !url.includes("/messages")) {
            return jsonResponse(chatSessionDetail);
          }
          if (url.includes("/api/v1/chat/sessions")) {
            return jsonResponse(chatSessionListResponse);
          }
          if (url.includes("/api/v1/corrections") && init?.method === "POST") {
            expect(String(init?.body)).toContain(chatSessionDetail.id);
            expect(String(init?.body)).toContain("chat_message_id");
            return jsonResponse(correctionDetail);
          }
          return jsonResponse({}, { status: 404 });
        })
      );

      render(
        <MemoryRouter initialEntries={[`/chat/${chatSessionDetail.id}`]}>
          <AppProviders>
            <Routes>
              <Route path="/chat/:sessionId" element={<ChatPage />} />
            </Routes>
          </AppProviders>
        </MemoryRouter>
      );

      await waitFor(() =>
        expect(
          screen.getByText(chatSessionDetail.messages?.[1].content ?? "")
        ).toBeInTheDocument()
      );
      expect(screen.getByText("assistant")).toBeInTheDocument();
      expect(screen.queryByText("degraded")).not.toBeInTheDocument();
      expect(screen.queryByText("combined")).not.toBeInTheDocument();
      expect(screen.queryByText("Suggestions")).not.toBeInTheDocument();
      expect(screen.queryByText(/chunk:1/)).not.toBeInTheDocument();
      expect(screen.queryByText("Implementation Plan (chunk:1) · document")).not.toBeInTheDocument();
      const sessionLink = await screen.findByRole("link", {
        name: /Architecture questions, updated/
      });
      expect(sessionLink).toHaveClass("grid");
      expect(sessionLink).toHaveClass("grid-cols-[minmax(0,1fr)_auto]");
      expect(sessionLink.querySelector("span:first-child")).toHaveClass("truncate");
      expect(sessionLink.querySelector("span:last-child")).toHaveClass("justify-self-end");
      expect(screen.getByText("10m")).toBeInTheDocument();
      expect(screen.queryByText(/2 messages · updated/)).not.toBeInTheDocument();
      expect(screen.getAllByText("document-first").length).toBeGreaterThan(0);

      const user = userEvent.setup();
      const citationsTrigger = screen.getByRole("button", { name: "Citations" });
      await user.hover(citationsTrigger);
      const citationLink = await screen.findByRole("link", {
        name: "Implementation Plan (line 12)"
      });
      expect(citationLink).toHaveAttribute("href", `/documents/${chatSessionDetail.document_id}`);

      await user.click(screen.getByRole("button", { name: "Submit correction" }));
      await user.type(
        screen.getByLabelText(/Proposed correction/),
        "Clarify the API service."
      );
      await user.click(screen.getByRole("button", { name: "Submit for review" }));

      await waitFor(() =>
        expect(screen.getByText("Correction submitted for review.")).toBeInTheDocument()
      );
    },
    10000
  );
});
