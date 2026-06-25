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
    "renders assistant-ui chat affordances and preserves existing chat actions",
    async () => {
      window.localStorage.setItem(AUTH_ACCESS_TOKEN_STORAGE_KEY, "token");
      vi.spyOn(Date, "now").mockReturnValue(new Date("2026-06-22T17:25:00Z").getTime());
      const sentMessages: string[] = [];

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
          if (url.includes("/api/v1/chat/sessions/") && url.includes("/messages")) {
            const body = JSON.parse(String(init?.body)) as { content: string };
            sentMessages.push(body.content);
            const userMessage = {
              content: body.content,
              created_at: "2026-06-22T17:16:00Z",
              degraded: false,
              id: `sent-user-${sentMessages.length}`,
              role: "user"
            };
            const assistantMessage = {
              citations: [],
              content: "The FastAPI app boots from ragdoll.main.",
              created_at: "2026-06-22T17:17:00Z",
              degraded: false,
              id: `sent-assistant-${sentMessages.length}`,
              retrieval_mode: "document",
              role: "assistant",
              suggestions: []
            };

            return jsonResponse({
              assistant_message: assistantMessage,
              session: {
                ...chatSessionDetail,
                message_count: (chatSessionDetail.messages?.length ?? 0) + 2,
                messages: [...(chatSessionDetail.messages ?? []), userMessage, assistantMessage],
                updated_at: "2026-06-22T17:17:00Z"
              },
              user_message: userMessage
            });
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
      expect(screen.queryByText("Retrieval chat")).not.toBeInTheDocument();
      expect(screen.queryByRole("heading", { name: "Chat", level: 1 })).not.toBeInTheDocument();
      expect(screen.queryByText(/Ask retrieval-backed questions/)).not.toBeInTheDocument();
      expect(screen.getByText("assistant")).toBeInTheDocument();
      expect(screen.getByText("degraded")).toBeInTheDocument();
      expect(screen.queryByText("combined")).not.toBeInTheDocument();
      expect(screen.queryByText("retrieval fallback")).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Send suggestion: Follow up" })).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Follow up" })).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: /model/i })).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: /provider/i })).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: /voice/i })).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: /attach/i })).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: /regenerate/i })).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: /^edit$/i })).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: /interrupt/i })).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: /pin/i })).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: /explain/i })).not.toBeInTheDocument();
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

      await user.type(screen.getByRole("textbox", { name: "Message" }), "Where does it boot?");
      await user.click(screen.getByRole("button", { name: "Send message" }));
      await waitFor(() => expect(sentMessages).toContain("Where does it boot?"));
    },
    10000
  );
});
