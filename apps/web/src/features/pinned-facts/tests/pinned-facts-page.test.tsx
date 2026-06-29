import type { ReactNode } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppProviders } from "../../../app/providers";
import { AUTH_ACCESS_TOKEN_STORAGE_KEY } from "../../../shared/state/authSession";
import { ACTIVE_SPACE_STORAGE_KEY, ALL_SPACES_STORAGE_KEY } from "../../../shared/state/spaceScope";
import {
  jsonResponse,
  pinnedFactCandidates,
  pinnedFactDetectionPreviewResponse,
  pinnedFactDetail,
  pinnedFactHistory,
  pinnedFactsListResponse,
  searchResponse,
  spaceListResponse,
  userProfile
} from "../../../test/testData";
import { PinnedFactCreatePage } from "../pages/PinnedFactCreatePage";
import { PinnedFactDetailPage } from "../pages/PinnedFactDetailPage";
import { PinnedFactsPage } from "../pages/PinnedFactsPage";

vi.mock("../../../shared/state/spaceScope", async () => {
  const actual = await vi.importActual<typeof import("../../../shared/state/spaceScope")>(
    "../../../shared/state/spaceScope"
  );
  const defaultSpace = {
    id: "33333333-3333-3333-3333-333333333333",
    name: "Core Space"
  };

  return {
    ...actual,
    SpaceScopeProvider: ({ children }: { children: ReactNode }) => children,
    useSpaceScope: () => {
      const allSpaces = window.localStorage.getItem(actual.ALL_SPACES_STORAGE_KEY) === "true";
      return {
        activeSpace: allSpaces ? null : defaultSpace,
        allSpaces,
        archivedSpaces: [],
        buildReadScopeParams: () => (allSpaces ? { all_spaces: true } : { space_id: defaultSpace.id }),
        isReady: true,
        refreshSpaces: async () => [defaultSpace],
        requireConcreteSpace: () => defaultSpace,
        setActiveSpace: vi.fn(),
        setAllSpaces: vi.fn(),
        spaces: [defaultSpace]
      };
    }
  };
});

function renderPinnedFactRoutes(initialEntries: Array<string | { pathname: string; state?: unknown }>) {
  render(
    <MemoryRouter initialEntries={initialEntries}>
      <AppProviders>
        <Routes>
          <Route path="/pinned-facts" element={<PinnedFactsPage />} />
          <Route path="/pinned-facts/create" element={<PinnedFactCreatePage />} />
          <Route path="/pinned-facts/:factId" element={<PinnedFactDetailPage />} />
        </Routes>
      </AppProviders>
    </MemoryRouter>
  );
}

describe("Pinned facts routes", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("renders list sorting and filtering controls and sorts by name by default", async () => {
    window.localStorage.setItem(AUTH_ACCESS_TOKEN_STORAGE_KEY, "token");

    const secondFact = {
      ...pinnedFactDetail,
      id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
      title: "API runtime",
      updated_at: "2026-06-23T17:05:00Z"
    };

    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        const requestUrl = new URL(url, "http://localhost");
        if (url.includes("/api/v1/auth/me")) {
          return jsonResponse(userProfile);
        }
        if (url.includes("/api/v1/spaces")) {
          return jsonResponse(spaceListResponse);
        }
        if (url.includes("/api/v1/pinned-facts")) {
          expect(requestUrl.searchParams.get("sort_key")).toBe("name");
          expect(requestUrl.searchParams.get("page_size")).toBe("100");
          const nameFilter = requestUrl.searchParams.get("name")?.toLowerCase() ?? "";
          const items = [secondFact, pinnedFactDetail].filter((item) =>
            nameFilter ? item.title.toLowerCase().includes(nameFilter) : true
          );
          return jsonResponse({
            ...pinnedFactsListResponse,
            items,
            total: items.length
          });
        }
        return jsonResponse({}, { status: 404 });
      })
    );

    renderPinnedFactRoutes(["/pinned-facts"]);

    await screen.findByText("API runtime");
    expect(screen.getByText("Current backend framework")).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText("Filter by name"), "backend");
    expect(screen.queryByText("API runtime")).not.toBeInTheDocument();
    expect(screen.getByText("Current backend framework")).toBeInTheDocument();
  });

  it("creates a pinned fact from the assistant preview answer and includes citation-matched evidence", async () => {
    window.localStorage.setItem(AUTH_ACCESS_TOKEN_STORAGE_KEY, "token");

    let createPayload: Record<string, unknown> | null = null;
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/api/v1/auth/me")) {
        return jsonResponse(userProfile);
      }
      if (url.includes("/api/v1/spaces")) {
        return jsonResponse(spaceListResponse);
      }
      if (url.includes("/api/v1/pinned-facts/detect-preview")) {
        return jsonResponse({
          ...pinnedFactDetectionPreviewResponse,
          assistant_message: {
            ...pinnedFactDetectionPreviewResponse.assistant_message,
            citations: [
              pinnedFactDetectionPreviewResponse.assistant_message.citations[0],
              {
                ...pinnedFactDetectionPreviewResponse.assistant_message.citations[0],
                chunk_id: "chunk-2",
                document_id: "66666666-6666-6666-6666-666666666666",
                locator: "chunk:2",
                title: "Frontend Build"
              }
            ],
            content: "- Frontend: FastAPI [E1]\n- Build: Vite [E2]",
            evidence: [
              {
                ...pinnedFactDetectionPreviewResponse.assistant_message.evidence[0],
                id: "E1",
                text: "FastAPI powers the API service."
              },
              {
                ...pinnedFactDetectionPreviewResponse.assistant_message.evidence[0],
                citations: [
                  {
                    ...pinnedFactDetectionPreviewResponse.assistant_message.citations[0],
                    chunk_id: "chunk-2",
                    document_id: "66666666-6666-6666-6666-666666666666",
                    locator: "chunk:2",
                    title: "Frontend Build"
                  }
                ],
                id: "E2",
                text: "Vite builds the frontend bundle."
              }
            ]
          },
          retrieval_results: [
            {
              ...searchResponse.items[0],
              matched_modes: ["combined"],
              preview_text: "FastAPI powers the API service."
            },
            {
              ...searchResponse.items[0],
              result_id: "second-result",
              matched_modes: ["combined"],
              preview_text: "Vite builds the frontend bundle."
            }
          ],
          source_document_id: null
        });
      }
      if (url.includes("/api/v1/pinned-facts") && init?.method === "POST") {
        createPayload = JSON.parse(String(init.body)) as Record<string, unknown>;
        return jsonResponse(pinnedFactDetail);
      }
      if (url.includes("/api/v1/pinned-facts")) {
        return jsonResponse(pinnedFactsListResponse);
      }
      return jsonResponse({}, { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);

    renderPinnedFactRoutes(["/pinned-facts/create"]);

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Name"), "Project color scheme");
    await user.type(screen.getByLabelText("Key"), "project_color_scheme");
    await user.type(screen.getByLabelText("Detection query"), "What is the current project color scheme?");
    await user.click(screen.getByRole("button", { name: "Test Query" }));

    await screen.findByText("Assistant preview");
    await user.click(screen.getByRole("button", { name: "Use as Stored Value" }));
    expect(screen.getByLabelText("Stored value")).toHaveValue("- Frontend: FastAPI\n- Build: Vite");
    await waitFor(() => expect(screen.getAllByText("Used for synthesis")).toHaveLength(2));
    await user.click(screen.getByRole("button", { name: "Create" }));

    await waitFor(() => expect(createPayload).not.toBeNull());
    expect((createPayload?.evidence as Array<unknown>).length).toBe(2);
    expect(createPayload).toMatchObject({
      source_document_id: null,
      value_text: "- Frontend: FastAPI\n- Build: Vite"
    });
  });

  it("shows a preview API error and still leaves create enabled for manual editing", async () => {
    window.localStorage.setItem(AUTH_ACCESS_TOKEN_STORAGE_KEY, "token");

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
        if (url.includes("/api/v1/pinned-facts/detect-preview")) {
          return Promise.resolve(
            new Response(
              JSON.stringify({
                detail: "Pinned fact detection could not reach the configured chat model.",
                status: 503,
                title: "Pinned fact detection unavailable",
                type: "https://ragdoll.dev/problems/pinned-fact-detection-unavailable"
              }),
              {
                headers: {
                  "Content-Type": "application/problem+json"
                },
                status: 503
              }
            )
          );
        }
        return jsonResponse({}, { status: 404 });
      })
    );

    renderPinnedFactRoutes(["/pinned-facts/create"]);

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Name"), "Project color scheme");
    await user.type(screen.getByLabelText("Key"), "project_color_scheme");
    await user.type(screen.getByLabelText("Detection query"), "What is the current project color scheme?");
    await user.type(screen.getByLabelText("Stored value"), "Atlas");
    await user.click(screen.getByRole("button", { name: "Test Query" }));

    await screen.findByText("The request failed without a structured problem response.");
    expect(screen.getByRole("button", { name: "Create" })).toBeEnabled();
  });

  it("creates a pinned fact from chat-seeded evidence without rerunning the query", async () => {
    window.localStorage.setItem(AUTH_ACCESS_TOKEN_STORAGE_KEY, "token");

    let createPayload: Record<string, unknown> | null = null;
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
        if (url.includes("/api/v1/pinned-facts") && init?.method === "POST") {
          createPayload = JSON.parse(String(init.body)) as Record<string, unknown>;
          return jsonResponse(pinnedFactDetail);
        }
        if (url.includes("/api/v1/pinned-facts")) {
          return jsonResponse(pinnedFactsListResponse);
        }
        return jsonResponse({}, { status: 404 });
      })
    );

    renderPinnedFactRoutes([
      {
        pathname: "/pinned-facts/create",
        state: {
          draft: {
            description: "What backend framework powers this repo today?",
            evidence: pinnedFactDetail.evidence,
            origin_label: "this chat answer",
            source_document_id: pinnedFactDetail.source_document_id,
            title: "Current backend framework",
            value_kind: "text",
            value_text: "FastAPI"
          }
        }
      }
    ]);

    const user = userEvent.setup();
    await screen.findByText("Seeded from chat");
    expect(screen.getByLabelText("Stored value")).toHaveValue("FastAPI");
    await user.type(screen.getByLabelText("Key"), "current_backend_framework");
    await user.click(screen.getByRole("button", { name: "Create" }));

    await waitFor(() => expect(createPayload).not.toBeNull());
    expect(createPayload).toMatchObject({
      description: "What backend framework powers this repo today?",
      source_document_id: pinnedFactDetail.source_document_id,
      title: "Current backend framework",
      value_text: "FastAPI"
    });
  });

  it("renders pending update review and manual edit actions on the detail page", async () => {
    window.localStorage.setItem(AUTH_ACCESS_TOKEN_STORAGE_KEY, "token");
    window.localStorage.setItem(ACTIVE_SPACE_STORAGE_KEY, spaceListResponse.items[0].id);

    let patchPayload: Record<string, unknown> | null = null;
    let accepted = false;

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
        if (url.includes("/accept")) {
          accepted = true;
          return jsonResponse(pinnedFactDetail);
        }
        if (url.includes(`/api/v1/pinned-facts/${pinnedFactDetail.id}`) && init?.method === "PATCH") {
          patchPayload = JSON.parse(String(init.body)) as Record<string, unknown>;
          return jsonResponse({
            ...pinnedFactDetail,
            value_text: "Starlette"
          });
        }
        if (url.includes("/candidates")) {
          return jsonResponse({
            items: [
              {
                ...pinnedFactCandidates.items[0],
                change_type: "evidence_update"
              }
            ]
          });
        }
        if (url.includes("/history")) {
          return jsonResponse(pinnedFactHistory);
        }
        if (url.includes(`/api/v1/pinned-facts/${pinnedFactDetail.id}`)) {
          return jsonResponse({
            ...pinnedFactDetail,
            status: "pending_update"
          });
        }
        return jsonResponse({}, { status: 404 });
      })
    );

    renderPinnedFactRoutes([`/pinned-facts/${pinnedFactDetail.id}`]);

    const user = userEvent.setup();
    await screen.findByText("Pending update detected");
    await screen.findByText("Review update");
    await user.click(screen.getByRole("button", { name: "Accept update" }));
    await waitFor(() => expect(accepted).toBe(true));

    await user.click(screen.getByRole("button", { name: "Edit stored value" }));
    await user.clear(screen.getByLabelText("Stored value"));
    await user.type(screen.getByLabelText("Stored value"), "Starlette");
    await user.type(screen.getByLabelText("Update note"), "Verified manually");
    await user.click(screen.getByRole("button", { name: "Save edit" }));
    await waitFor(() => expect(patchPayload).not.toBeNull());
    expect(patchPayload).toMatchObject({
      update_note: "Verified manually",
      value_kind: "text",
      value_text: "Starlette"
    });
  });

  it("disables pinned-fact writes while all-spaces mode is active", async () => {
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
        if (url.includes("/api/v1/pinned-facts")) {
          return jsonResponse(pinnedFactsListResponse);
        }
        return jsonResponse({}, { status: 404 });
      })
    );

    renderPinnedFactRoutes(["/pinned-facts"]);

    await waitFor(() =>
      expect(
        screen.getByText("Choose one active Space before creating or editing pinned facts.")
      ).toBeInTheDocument()
    );
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Create Fact" })).toBeDisabled()
    );
  });
});
