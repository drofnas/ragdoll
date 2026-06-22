import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppProviders } from "../../../app/providers";
import { AUTH_ACCESS_TOKEN_STORAGE_KEY } from "../../../shared/state/authSession";
import { DocumentDetailPage } from "../pages/DocumentDetailPage";
import { DocumentsPage } from "../pages/DocumentsPage";
import {
  documentDetail,
  documentListResponse,
  documentStatusResponse,
  jsonResponse,
  spaces,
  spaceListResponse,
  userProfile
} from "../../../test/testData";

describe("DocumentsPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("uploads a file and routes to the document detail page", async () => {
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
        if (url.includes(`/api/v1/documents/${documentDetail.id}`) && (!init?.method || init.method === "GET")) {
          return jsonResponse(documentDetail);
        }
        if (url.includes(`/api/v1/ingestion/documents/${documentDetail.id}/status`)) {
          return jsonResponse(documentStatusResponse);
        }
        if (url.includes("/api/v1/documents") && (!init?.method || init.method === "GET")) {
          return jsonResponse(documentListResponse);
        }
        if (url.includes("/api/v1/ingestion/uploads")) {
          expect(url).toContain(`space_id=${spaces[0].id}`);
          return jsonResponse(
            {
              document_id: documentDetail.id,
              filename: documentDetail.original_filename,
              job_id: "66666666-6666-6666-6666-666666666666",
              processing_status: documentStatusResponse.processing_status
            },
            { status: 201 }
          );
        }
        return jsonResponse({}, { status: 404 });
      })
    );

    const { container } = render(
      <MemoryRouter initialEntries={["/documents"]}>
        <AppProviders>
          <Routes>
            <Route path="/documents" element={<DocumentsPage />} />
            <Route path="/documents/:documentId" element={<DocumentDetailPage />} />
          </Routes>
        </AppProviders>
      </MemoryRouter>
    );

    await waitFor(() => expect(screen.getByText("Documents")).toBeInTheDocument());
    const user = userEvent.setup();
    const fileInput = container.querySelector("input[type='file']") as HTMLInputElement;
    await user.upload(fileInput, new File(["hello"], "plan.pdf", { type: "application/pdf" }));
    await user.click(screen.getByRole("button", { name: "Upload" }));

    await waitFor(() => expect(screen.getByText(documentDetail.title)).toBeInTheDocument());
  });
});
