import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppProviders } from "../../../app/providers";
import { AUTH_ACCESS_TOKEN_STORAGE_KEY } from "../../../shared/state/authSession";
import { DocumentDetailPage } from "../pages/DocumentDetailPage";
import { DocumentsPage } from "../pages/DocumentsPage";
import {
  chatSessionDetail,
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
    vi.useRealTimers();
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

  it("reprocesses a failed document from the detail page", async () => {
    window.localStorage.setItem(AUTH_ACCESS_TOKEN_STORAGE_KEY, "token");

    const failedStatus = {
      ...documentStatusResponse,
      latest_job: {
        ...documentStatusResponse.latest_job!,
        status: "failed" as const,
        visible_error_detail: "Expecting value: line 1 column 1 (char 0)",
      },
      processing_status: {
        ...documentStatusResponse.processing_status,
        detail: "Expecting value: line 1 column 1 (char 0)",
        extraction: "failed" as const,
        graph: "pending" as const,
        overall: "failed" as const,
      },
    };
    const pendingStatus = {
      ...failedStatus,
      latest_job: {
        ...failedStatus.latest_job!,
        status: "queued" as const,
        visible_error_detail: null,
      },
      processing_status: {
        ...failedStatus.processing_status,
        detail: null,
        extraction: "pending" as const,
        overall: "pending" as const,
      },
    };
    let currentStatus = failedStatus;

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
          return jsonResponse({
            ...documentDetail,
            processing_status: currentStatus.processing_status,
          });
        }
        if (url.includes(`/api/v1/ingestion/documents/${documentDetail.id}/reprocess`) && init?.method === "POST") {
          currentStatus = pendingStatus;
          return jsonResponse(currentStatus);
        }
        if (url.includes(`/api/v1/ingestion/documents/${documentDetail.id}/status`)) {
          return jsonResponse(currentStatus);
        }
        return jsonResponse({}, { status: 404 });
      })
    );

    render(
      <MemoryRouter initialEntries={[`/documents/${documentDetail.id}`]}>
        <AppProviders>
          <Routes>
            <Route path="/documents/:documentId" element={<DocumentDetailPage />} />
          </Routes>
        </AppProviders>
      </MemoryRouter>
    );

    await waitFor(() => expect(screen.getByText("Overall: failed")).toBeInTheDocument());

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Reprocess document" }));

    await waitFor(() => expect(screen.getByText("Overall: pending")).toBeInTheDocument());
    expect(screen.getByText("Latest job: queued")).toBeInTheDocument();
  });

  it("starts a document-first chat session from the document detail page", async () => {
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
        if (url.includes("/api/v1/chat/sessions") && init?.method === "POST") {
          expect(url).toContain(`space_id=${documentDetail.space_id}`);
          expect(url).toContain(`document_id=${documentDetail.id}`);
          return jsonResponse({
            ...chatSessionDetail,
            id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            message_count: 0,
            messages: [],
            title: "New chat",
          });
        }
        return jsonResponse({}, { status: 404 });
      })
    );

    render(
      <MemoryRouter initialEntries={[`/documents/${documentDetail.id}`]}>
        <AppProviders>
          <Routes>
            <Route path="/documents/:documentId" element={<DocumentDetailPage />} />
            <Route path="/chat/:sessionId" element={<div>Chat opened</div>} />
          </Routes>
        </AppProviders>
      </MemoryRouter>
    );

    await waitFor(() => expect(screen.getByText(documentDetail.title)).toBeInTheDocument());

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Chat about this document" }));

    await waitFor(() => expect(screen.getByText("Chat opened")).toBeInTheDocument());
  });

  it("shows extraction progress details for long-running document jobs", async () => {
    vi.spyOn(Date, "now").mockReturnValue(new Date("2026-06-22T17:15:30Z").getTime());
    window.localStorage.setItem(AUTH_ACCESS_TOKEN_STORAGE_KEY, "token");

    const processingStatus = {
      ...documentStatusResponse,
      chunk_count: 113,
      latest_job: {
        ...documentStatusResponse.latest_job!,
        completed_at: null,
        started_at: "2026-06-22T17:05:00Z",
        status: "processing" as const,
      },
      processing_status: {
        ...documentStatusResponse.processing_status,
        extraction: "processing" as const,
        graph: "pending" as const,
        overall: "processing" as const,
        vector: "completed" as const,
      },
    };

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
          return jsonResponse({
            ...documentDetail,
            processing_status: processingStatus.processing_status,
          });
        }
        if (url.includes(`/api/v1/ingestion/documents/${documentDetail.id}/status`)) {
          return jsonResponse(processingStatus);
        }
        return jsonResponse({}, { status: 404 });
      })
    );

    render(
      <MemoryRouter initialEntries={[`/documents/${documentDetail.id}`]}>
        <AppProviders>
          <Routes>
            <Route path="/documents/:documentId" element={<DocumentDetailPage />} />
          </Routes>
        </AppProviders>
      </MemoryRouter>
    );

    await waitFor(() => expect(screen.getByText("Latest job: processing")).toBeInTheDocument());
    expect(screen.getByText((content) => content.startsWith("Started:"))).toBeInTheDocument();
    expect(screen.getByText("Elapsed: 10m 30s")).toBeInTheDocument();
    expect(screen.getByText(/processed chunk-by-chunk locally/i)).toBeInTheDocument();
    expect(screen.getByText(/113 chunks/i)).toBeInTheDocument();
  });
});
