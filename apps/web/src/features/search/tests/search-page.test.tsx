import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppProviders } from "../../../app/providers";
import { AUTH_ACCESS_TOKEN_STORAGE_KEY } from "../../../shared/state/authSession";
import { SearchPage } from "../pages/SearchPage";
import {
  documentDetail,
  jsonResponse,
  searchResponse,
  spaceListResponse,
  userProfile
} from "../../../test/testData";

describe("SearchPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("reads URL params, renders retrieval results, and submits a new search query", async () => {
    window.localStorage.setItem(AUTH_ACCESS_TOKEN_STORAGE_KEY, "token");

    const seenSearchUrls: string[] = [];
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
        if (url.includes("/api/v1/search")) {
          seenSearchUrls.push(url);
          if (url.includes("q=OpenAPI")) {
            return jsonResponse({
              ...searchResponse,
              items: [
                {
                  ...searchResponse.items[0],
                  preview_text: "OpenAPI exports stay aligned with the FastAPI surface.",
                  result_id: "search-result-2"
                }
              ]
            });
          }
          return jsonResponse(searchResponse);
        }
        return jsonResponse({}, { status: 404 });
      })
    );

    render(
      <MemoryRouter initialEntries={["/search?q=FastAPI&mode=vector"]}>
        <AppProviders>
          <Routes>
            <Route path="/search" element={<SearchPage />} />
          </Routes>
        </AppProviders>
      </MemoryRouter>
    );

    await waitFor(() => expect(seenSearchUrls.length).toBeGreaterThan(0));
    await waitFor(() =>
      expect(screen.getByText(documentDetail.title)).toBeInTheDocument()
    );
    expect(seenSearchUrls.some((url) => url.includes("mode=vector"))).toBe(true);
    expect(screen.getByRole("link", { name: "Open document" })).toHaveAttribute(
      "href",
      `/documents/${documentDetail.id}`
    );

    const user = userEvent.setup();
    await user.clear(screen.getByLabelText(/Search query/));
    await user.type(screen.getByLabelText(/Search query/), "OpenAPI");
    await user.click(screen.getByRole("button", { name: "Run search" }));

    await waitFor(() =>
      expect(seenSearchUrls.some((url) => url.includes("q=OpenAPI"))).toBe(true)
    );
    await waitFor(() =>
      expect(
        screen.getByText("OpenAPI exports stay aligned with the FastAPI surface.")
      ).toBeInTheDocument()
    );
  }, 15000);
});
