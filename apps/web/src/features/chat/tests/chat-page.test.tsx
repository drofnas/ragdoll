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
    "renders a degraded assistant answer and submits a correction from the transcript",
    async () => {
    window.localStorage.setItem(AUTH_ACCESS_TOKEN_STORAGE_KEY, "token");

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
      expect(screen.getByText("degraded")).toBeInTheDocument();

      const user = userEvent.setup();
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
