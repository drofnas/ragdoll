import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppProviders } from "../../../app/providers";
import { AUTH_ACCESS_TOKEN_STORAGE_KEY } from "../../../shared/state/authSession";
import { ALL_SPACES_STORAGE_KEY } from "../../../shared/state/spaceScope";
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

function buildDocumentListItem(id: string, filename: string) {
  return {
    ...documentDetail,
    id,
    original_filename: filename,
    title: filename,
    processing_status: {
      ...documentDetail.processing_status,
      overall: "completed" as const
    }
  };
}

function expectProgressState(
  row: HTMLTableRowElement,
  name: string,
  value: string,
  indicatorClassName: string
) {
  const progressbar = within(row).getByRole("progressbar", { name });
  expect(progressbar).toHaveAttribute("aria-valuenow", value);
  expect(progressbar.firstElementChild).toHaveClass(indicatorClassName);
}

describe("DocumentsPage", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("uploads multiple files and keeps the user on the library page", async () => {
    window.localStorage.setItem(AUTH_ACCESS_TOKEN_STORAGE_KEY, "token");

    const uploadedDocuments = [buildDocumentListItem(documentDetail.id, documentDetail.original_filename)];
    let uploadCallCount = 0;

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
        if (url.includes("/api/v1/ingestion/documents/status/batch") && init?.method === "POST") {
          return jsonResponse({
            statuses: uploadedDocuments.map((document) => ({
              ...documentStatusResponse,
              document_id: document.id,
              processing_status: document.processing_status
            }))
          });
        }
        if (url.includes("/api/v1/documents") && (!init?.method || init.method === "GET")) {
          return jsonResponse({
            ...documentListResponse,
            items: uploadedDocuments,
            total: uploadedDocuments.length
          });
        }
        if (url.includes("/api/v1/ingestion/uploads")) {
          uploadCallCount += 1;
          const nextDocument = buildDocumentListItem(
            `uploaded-${uploadCallCount}`,
            uploadCallCount === 1 ? "brief.pdf" : "notes.md"
          );
          uploadedDocuments.unshift(nextDocument);
          expect(url).toContain(`space_id=${spaces[0].id}`);
          return jsonResponse(
            {
              document_id: nextDocument.id,
              filename: nextDocument.original_filename,
              job_id: `job-${uploadCallCount}`,
              processing_status: {
                ...documentStatusResponse.processing_status,
                overall: "pending"
              }
            },
            { status: 201 }
          );
        }
        return jsonResponse({}, { status: 404 });
      })
    );

    render(
      <MemoryRouter initialEntries={["/documents"]}>
        <AppProviders>
          <Routes>
            <Route path="/documents" element={<DocumentsPage />} />
          </Routes>
        </AppProviders>
      </MemoryRouter>
    );

    await waitFor(() => expect(screen.getByRole("heading", { name: "Library" })).toBeInTheDocument());
    expect(screen.queryByText("Filter the library")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Upload documents" })).not.toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByRole("link", { name: "View" })).toHaveAttribute(
        "href",
        `/documents/${documentDetail.id}`
      )
    );
    expect(screen.getByRole("columnheader", { name: "Chunk Status" })).toBeInTheDocument();
    expect(screen.queryByRole("columnheader", { name: "Chunks" })).not.toBeInTheDocument();
    expect(screen.queryByRole("columnheader", { name: "Status" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "View Details" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Upload" })).toBeInTheDocument();

    const filterLabel = screen.getByText("Filter");
    expect(filterLabel.parentElement).toHaveClass("items-center");
    expect(filterLabel.parentElement?.parentElement).toHaveClass("md:flex-row");

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Upload" }));

    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByRole("heading", { name: "Upload documents" })).toBeInTheDocument();
    expect(within(dialog).getByText("Target Space:")).toBeInTheDocument();
    expect(within(dialog).getByText("Core Space")).toBeInTheDocument();

    const fileInput = within(dialog).getByLabelText("Upload documents") as HTMLInputElement;
    await user.upload(fileInput, [
      new File(["brief"], "brief.pdf", { type: "application/pdf" }),
      new File(["notes"], "notes.md", { type: "text/markdown" })
    ]);

    await waitFor(() => expect(uploadCallCount).toBe(2));
    await waitFor(() => expect(screen.getAllByText("brief.pdf").length).toBeGreaterThan(0));
    expect(screen.getAllByText("notes.md").length).toBeGreaterThan(0);
    expect(screen.queryByRole("heading", { name: "Metadata" })).not.toBeInTheDocument();
  });

  it("opens a disabled upload modal when all Spaces are active", async () => {
    window.localStorage.setItem(AUTH_ACCESS_TOKEN_STORAGE_KEY, "token");
    window.localStorage.setItem(ALL_SPACES_STORAGE_KEY, "true");

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
        if (url.includes("/api/v1/documents") && (!init?.method || init.method === "GET")) {
          return jsonResponse(documentListResponse);
        }
        if (url.includes("/api/v1/ingestion/documents/status/batch") && init?.method === "POST") {
          return jsonResponse({
            statuses: [documentStatusResponse]
          });
        }
        return jsonResponse({}, { status: 404 });
      })
    );

    render(
      <MemoryRouter initialEntries={["/documents"]}>
        <AppProviders>
          <Routes>
            <Route path="/documents" element={<DocumentsPage />} />
          </Routes>
        </AppProviders>
      </MemoryRouter>
    );

    await waitFor(() =>
      expect(screen.getByText("Read scope spans all Spaces")).toBeInTheDocument()
    );

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Upload" }));

    const dialog = await screen.findByRole("dialog");
    expect(
      within(dialog).getByText("Choose one active Space in the shell selector to enable uploads.")
    ).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Choose files" })).toBeDisabled();
  });

  it("disables refresh for queued and active library rows, but keeps terminal rows refreshable", async () => {
    window.localStorage.setItem(AUTH_ACCESS_TOKEN_STORAGE_KEY, "token");

    const queuedDocument = {
      ...buildDocumentListItem("queued-document", "queued.pdf"),
      chunk_count: 12,
      indexed_chunk_count: 0,
      processing_status: {
        ...documentDetail.processing_status,
        extraction: "pending" as const,
        graph: "pending" as const,
        overall: "pending" as const,
        parsing: "pending" as const,
        vector: "pending" as const
      }
    };
    const refreshStartDocument = {
      ...buildDocumentListItem("refresh-start-document", "refresh-start.pdf"),
      chunk_count: 12,
      indexed_chunk_count: 12,
      processing_status: {
        ...documentDetail.processing_status,
        extraction: "pending" as const,
        graph: "pending" as const,
        overall: "processing" as const,
        parsing: "processing" as const,
        vector: "pending" as const
      }
    };
    const parsingProgressDocument = {
      ...buildDocumentListItem("parsing-progress-document", "parsing-progress.pdf"),
      chunk_count: 12,
      indexed_chunk_count: 12,
      processing_status: {
        ...documentDetail.processing_status,
        extraction: "pending" as const,
        graph: "pending" as const,
        overall: "processing" as const,
        parsing: "processing" as const,
        vector: "pending" as const
      }
    };
    const processingDocument = {
      ...buildDocumentListItem("processing-document", "processing.pdf"),
      chunk_count: 12,
      indexed_chunk_count: 6,
      processing_status: {
        ...documentDetail.processing_status,
        overall: "processing" as const,
        parsing: "completed" as const,
        vector: "processing" as const,
        extraction: "pending" as const,
        graph: "pending" as const
      }
    };
    const extractionProgressDocument = {
      ...buildDocumentListItem("extraction-progress-document", "extraction-progress.pdf"),
      chunk_count: 12,
      indexed_chunk_count: 12,
      processing_status: {
        ...documentDetail.processing_status,
        extraction: "processing" as const,
        graph: "pending" as const,
        overall: "processing" as const,
        parsing: "completed" as const,
        vector: "completed" as const
      }
    };
    const vectorStartDocument = {
      ...buildDocumentListItem("vector-start-document", "vector-start.pdf"),
      chunk_count: 12,
      indexed_chunk_count: 12,
      processing_status: {
        ...documentDetail.processing_status,
        overall: "processing" as const,
        parsing: "completed" as const,
        vector: "processing" as const,
        extraction: "pending" as const,
        graph: "pending" as const
      }
    };
    const graphingDocument = {
      ...buildDocumentListItem("graphing-document", "graphing.pdf"),
      chunk_count: 12,
      indexed_chunk_count: 9,
      processing_status: {
        ...documentDetail.processing_status,
        extraction: "completed" as const,
        graph: "processing" as const,
        overall: "processing" as const,
        parsing: "completed" as const,
        vector: "completed" as const
      }
    };
    const staleRuntimeDocument = {
      ...buildDocumentListItem("stale-runtime-document", "stale-runtime.pdf"),
      chunk_count: 12,
      indexed_chunk_count: 12,
      processing_status: {
        ...documentDetail.processing_status,
        extraction: "processing" as const,
        graph: "pending" as const,
        overall: "processing" as const,
        parsing: "completed" as const,
        vector: "completed" as const
      }
    };
    const completedDocument = {
      ...buildDocumentListItem("completed-document", "completed.pdf"),
      chunk_count: 12,
      indexed_chunk_count: 12
    };
    const failedDocument = {
      ...buildDocumentListItem("failed-document", "failed.pdf"),
      chunk_count: 12,
      indexed_chunk_count: 3,
      processing_status: {
        ...documentDetail.processing_status,
        detail: "Could not parse the extracted text",
        extraction: "failed" as const,
        graph: "pending" as const,
        overall: "failed" as const
      }
    };
    const failedQueuedDocument = {
      ...buildDocumentListItem("failed-queued-document", "failed-queued.pdf"),
      chunk_count: 12,
      indexed_chunk_count: 3,
      processing_status: failedDocument.processing_status
    };
    const statuses = [
      {
        ...documentStatusResponse,
        chunk_count: 12,
        document_id: queuedDocument.id,
        indexed_chunk_count: 0,
        queue_runtime: {
          chunk_progress_current: 0,
          chunk_progress_total: 12,
          detail: null,
          enqueued_at: "2026-06-22T17:01:00Z",
          ended_at: null,
          job_id: documentStatusResponse.latest_job!.id,
          queue_job_id: documentStatusResponse.latest_job!.id,
          queue_name: "document-processing",
          queue_position: 2,
          stage: "parsing",
          started_at: null,
          status: "queued",
          updated_at: "2026-06-22T17:01:00Z",
          worker_name: null
        },
        processing_status: queuedDocument.processing_status,
        queued_job_count: 0
      },
      {
        ...documentStatusResponse,
        active_job: {
          ...documentStatusResponse.latest_job!,
          completed_at: null,
          requested_stage: "parsing",
          started_at: "2026-06-22T17:01:00Z",
          status: "processing" as const
        },
        chunk_count: 12,
        document_id: refreshStartDocument.id,
        indexed_chunk_count: 12,
        latest_job: {
          ...documentStatusResponse.latest_job!,
          completed_at: null,
          requested_stage: "parsing",
          started_at: "2026-06-22T17:01:00Z",
          status: "processing" as const
        },
        processing_status: refreshStartDocument.processing_status,
        queued_job_count: 0
      },
      {
        ...documentStatusResponse,
        active_job: {
          ...documentStatusResponse.latest_job!,
          completed_at: null,
          requested_stage: "parsing",
          started_at: "2026-06-22T17:01:15Z",
          status: "processing" as const
        },
        chunk_count: 12,
        document_id: parsingProgressDocument.id,
        indexed_chunk_count: 12,
        latest_job: {
          ...documentStatusResponse.latest_job!,
          completed_at: null,
          requested_stage: "parsing",
          started_at: "2026-06-22T17:01:15Z",
          status: "processing" as const
        },
        queue_runtime: {
          chunk_progress_current: 6,
          chunk_progress_total: 12,
          detail: null,
          enqueued_at: "2026-06-22T17:01:00Z",
          ended_at: null,
          job_id: documentStatusResponse.latest_job!.id,
          queue_job_id: documentStatusResponse.latest_job!.id,
          queue_name: "document-processing",
          queue_position: null,
          stage: "parsing",
          started_at: "2026-06-22T17:01:15Z",
          status: "started",
          updated_at: "2026-06-22T17:01:20Z",
          worker_name: "rq:worker-1"
        },
        processing_status: parsingProgressDocument.processing_status,
        queued_job_count: 0
      },
      {
        ...documentStatusResponse,
        active_job: {
          ...documentStatusResponse.latest_job!,
          completed_at: null,
          requested_stage: "parsing",
          started_at: "2026-06-22T17:01:30Z",
          status: "processing" as const
        },
        chunk_count: 12,
        document_id: vectorStartDocument.id,
        indexed_chunk_count: 12,
        latest_job: {
          ...documentStatusResponse.latest_job!,
          completed_at: null,
          requested_stage: "parsing",
          started_at: "2026-06-22T17:01:30Z",
          status: "processing" as const
        },
        processing_status: vectorStartDocument.processing_status,
        queued_job_count: 0
      },
      {
        ...documentStatusResponse,
        active_job: {
          ...documentStatusResponse.latest_job!,
          completed_at: null,
          requested_stage: "parsing",
          started_at: "2026-06-22T17:02:00Z",
          status: "processing" as const
        },
        chunk_count: 12,
        document_id: processingDocument.id,
        indexed_chunk_count: 6,
        latest_job: {
          ...documentStatusResponse.latest_job!,
          completed_at: null,
          requested_stage: "parsing",
          started_at: "2026-06-22T17:02:00Z",
          status: "processing" as const
        },
        queue_runtime: {
          chunk_progress_current: 6,
          chunk_progress_total: 12,
          detail: null,
          enqueued_at: "2026-06-22T17:01:00Z",
          ended_at: null,
          job_id: documentStatusResponse.latest_job!.id,
          queue_job_id: documentStatusResponse.latest_job!.id,
          queue_name: "document-processing",
          queue_position: null,
          stage: "vector",
          started_at: "2026-06-22T17:02:00Z",
          status: "started",
          updated_at: "2026-06-22T17:02:30Z",
          worker_name: "rq:worker-1"
        },
        processing_status: processingDocument.processing_status,
        queued_job_count: 0
      },
      {
        ...documentStatusResponse,
        active_job: {
          ...documentStatusResponse.latest_job!,
          completed_at: null,
          requested_stage: "parsing",
          started_at: "2026-06-22T17:05:00Z",
          status: "processing" as const
        },
        chunk_count: 12,
        document_id: extractionProgressDocument.id,
        indexed_chunk_count: 12,
        latest_job: {
          ...documentStatusResponse.latest_job!,
          completed_at: null,
          requested_stage: "parsing",
          started_at: "2026-06-22T17:05:00Z",
          status: "processing" as const
        },
        queue_runtime: {
          chunk_progress_current: 3,
          chunk_progress_total: 12,
          detail: null,
          enqueued_at: "2026-06-22T17:04:00Z",
          ended_at: null,
          job_id: documentStatusResponse.latest_job!.id,
          queue_job_id: documentStatusResponse.latest_job!.id,
          queue_name: "document-processing",
          queue_position: null,
          stage: "extraction",
          started_at: "2026-06-22T17:05:00Z",
          status: "started",
          updated_at: "2026-06-22T17:05:20Z",
          worker_name: "rq:worker-2"
        },
        processing_status: extractionProgressDocument.processing_status,
        queued_job_count: 0
      },
      {
        ...documentStatusResponse,
        active_job: {
          ...documentStatusResponse.latest_job!,
          completed_at: null,
          requested_stage: "parsing",
          started_at: "2026-06-22T17:08:00Z",
          status: "processing" as const
        },
        chunk_count: 12,
        document_id: graphingDocument.id,
        indexed_chunk_count: 9,
        latest_job: {
          ...documentStatusResponse.latest_job!,
          completed_at: null,
          requested_stage: "parsing",
          started_at: "2026-06-22T17:08:00Z",
          status: "processing" as const
        },
        queue_runtime: {
          chunk_progress_current: 9,
          chunk_progress_total: 12,
          detail: null,
          enqueued_at: "2026-06-22T17:07:00Z",
          ended_at: null,
          job_id: documentStatusResponse.latest_job!.id,
          queue_job_id: documentStatusResponse.latest_job!.id,
          queue_name: "document-processing",
          queue_position: null,
          stage: "graph",
          started_at: "2026-06-22T17:08:00Z",
          status: "started",
          updated_at: "2026-06-22T17:08:30Z",
          worker_name: "rq:worker-2"
        },
        processing_status: graphingDocument.processing_status,
        queued_job_count: 0
      },
      {
        ...documentStatusResponse,
        active_job: {
          ...documentStatusResponse.latest_job!,
          completed_at: null,
          requested_stage: "parsing",
          started_at: "2026-06-22T17:09:00Z",
          status: "processing" as const
        },
        chunk_count: 12,
        document_id: staleRuntimeDocument.id,
        indexed_chunk_count: 12,
        latest_job: {
          ...documentStatusResponse.latest_job!,
          completed_at: null,
          requested_stage: "parsing",
          started_at: "2026-06-22T17:09:00Z",
          status: "processing" as const
        },
        queue_runtime: {
          chunk_progress_current: 12,
          chunk_progress_total: 12,
          detail: null,
          enqueued_at: "2026-06-22T17:08:00Z",
          ended_at: null,
          job_id: documentStatusResponse.latest_job!.id,
          queue_job_id: documentStatusResponse.latest_job!.id,
          queue_name: "document-processing",
          queue_position: null,
          stage: "vector",
          started_at: "2026-06-22T17:09:00Z",
          status: "started",
          updated_at: "2026-06-22T17:09:30Z",
          worker_name: "rq:worker-3"
        },
        processing_status: staleRuntimeDocument.processing_status,
        queued_job_count: 0
      },
      {
        ...documentStatusResponse,
        chunk_count: 12,
        document_id: completedDocument.id,
        indexed_chunk_count: 12,
        processing_status: completedDocument.processing_status,
        queued_job_count: 0
      },
      {
        ...documentStatusResponse,
        chunk_count: 12,
        document_id: failedDocument.id,
        indexed_chunk_count: 3,
        latest_job: {
          ...documentStatusResponse.latest_job!,
          status: "failed" as const,
          visible_error_detail: "Could not parse the extracted text"
        },
        processing_status: failedDocument.processing_status,
        queued_job_count: 0
      },
      {
        ...documentStatusResponse,
        chunk_count: 12,
        document_id: failedQueuedDocument.id,
        has_queued_reprocess: true,
        indexed_chunk_count: 3,
        latest_job: {
          ...documentStatusResponse.latest_job!,
          completed_at: null,
          started_at: null,
          status: "queued" as const,
          visible_error_detail: null
        },
        processing_status: failedQueuedDocument.processing_status,
        queued_job_count: 1
      }
    ];

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
        if (url.includes("/api/v1/ingestion/documents/status/batch") && init?.method === "POST") {
          return jsonResponse({
            statuses
          });
        }
        if (url.includes("/api/v1/documents") && (!init?.method || init.method === "GET")) {
          return jsonResponse({
            ...documentListResponse,
            items: [
              queuedDocument,
              refreshStartDocument,
              parsingProgressDocument,
              vectorStartDocument,
              processingDocument,
              extractionProgressDocument,
              graphingDocument,
              staleRuntimeDocument,
              completedDocument,
              failedDocument,
              failedQueuedDocument
            ],
            total: 11
          });
        }
        return jsonResponse({}, { status: 404 });
      })
    );

    render(
      <MemoryRouter initialEntries={["/documents"]}>
        <AppProviders>
          <Routes>
            <Route path="/documents" element={<DocumentsPage />} />
          </Routes>
        </AppProviders>
      </MemoryRouter>
    );

    await waitFor(() => expect(screen.getByText("Queued")).toBeInTheDocument());

    const queuedRow = screen.getByText("queued.pdf").closest("tr")!;
    const refreshStartRow = screen.getByText("refresh-start.pdf").closest("tr")!;
    const parsingProgressRow = screen.getByText("parsing-progress.pdf").closest("tr")!;
    const vectorStartRow = screen.getByText("vector-start.pdf").closest("tr")!;
    const processingRow = screen.getByText("processing.pdf").closest("tr")!;
    const extractionProgressRow = screen.getByText("extraction-progress.pdf").closest("tr")!;
    const graphingRow = screen.getByText("graphing.pdf").closest("tr")!;
    const staleRuntimeRow = screen.getByText("stale-runtime.pdf").closest("tr")!;
    const completedRow = screen.getByText("completed.pdf").closest("tr")!;
    const failedRow = screen.getByText("failed.pdf").closest("tr")!;
    const failedQueuedRow = screen.getByText("failed-queued.pdf").closest("tr")!;

    expect(within(queuedRow).getByText("Queued")).toBeInTheDocument();
    expect(within(queuedRow).getByText("0%")).toBeInTheDocument();
    expectProgressState(queuedRow, "Queued chunk progress", "0", "bg-muted-foreground/30");

    expect(within(refreshStartRow).getByText("0%")).toBeInTheDocument();
    expect(within(refreshStartRow).getByText("Parsing")).toBeInTheDocument();
    expectProgressState(refreshStartRow, "Parsing chunk progress", "0", "bg-sky-600");

    await waitFor(() => expect(within(parsingProgressRow).getByText("Parsing")).toBeInTheDocument());
    expect(within(parsingProgressRow).getByText("13%")).toBeInTheDocument();
    expectProgressState(parsingProgressRow, "Parsing chunk progress", "13", "bg-sky-600");

    await waitFor(() => expect(within(vectorStartRow).getByText("Vectorizing")).toBeInTheDocument());
    expect(within(vectorStartRow).getByText("25%")).toBeInTheDocument();
    expectProgressState(vectorStartRow, "Vectorizing chunk progress", "25", "bg-sky-600");

    await waitFor(() => expect(within(processingRow).getByText("Vectorizing")).toBeInTheDocument());
    expect(within(processingRow).getByText("38%")).toBeInTheDocument();
    expectProgressState(processingRow, "Vectorizing chunk progress", "38", "bg-sky-600");

    await waitFor(() => expect(within(extractionProgressRow).getByText("Extracting")).toBeInTheDocument());
    expect(within(extractionProgressRow).getByText("56%")).toBeInTheDocument();
    expectProgressState(extractionProgressRow, "Extracting chunk progress", "56", "bg-sky-600");

    await waitFor(() => expect(within(graphingRow).getByText("Graphing")).toBeInTheDocument());
    expect(within(graphingRow).getByText("94%")).toBeInTheDocument();
    expectProgressState(graphingRow, "Graphing chunk progress", "94", "bg-sky-600");

    await waitFor(() => expect(within(staleRuntimeRow).getByText("Extracting")).toBeInTheDocument());
    expect(within(staleRuntimeRow).getByText("50%")).toBeInTheDocument();
    expectProgressState(staleRuntimeRow, "Extracting chunk progress", "50", "bg-sky-600");

    expect(within(completedRow).getByText("Completed")).toBeInTheDocument();
    expect(within(completedRow).getByText("12")).toBeInTheDocument();
    expectProgressState(completedRow, "Completed chunk progress", "100", "bg-primary");

    expect(within(failedRow).getByText("Failed")).toBeInTheDocument();
    expect(within(failedRow).getByText("12")).toBeInTheDocument();
    expectProgressState(failedRow, "Failed chunk progress", "50", "bg-destructive");

    await waitFor(() => expect(within(failedQueuedRow).getByText("Queued")).toBeInTheDocument());
    expect(within(failedQueuedRow).getByText("0%")).toBeInTheDocument();
    expectProgressState(failedQueuedRow, "Queued chunk progress", "0", "bg-muted-foreground/30");

    expect(within(queuedRow).getByRole("button", { name: "Refresh" })).toBeDisabled();
    expect(within(refreshStartRow).getByRole("button", { name: "Refresh" })).toBeDisabled();
    expect(within(parsingProgressRow).getByRole("button", { name: "Refresh" })).toBeDisabled();
    expect(within(vectorStartRow).getByRole("button", { name: "Refresh" })).toBeDisabled();
    expect(within(processingRow).getByRole("button", { name: "Refresh" })).toBeDisabled();
    expect(within(extractionProgressRow).getByRole("button", { name: "Refresh" })).toBeDisabled();
    expect(within(graphingRow).getByRole("button", { name: "Refresh" })).toBeDisabled();
    expect(within(staleRuntimeRow).getByRole("button", { name: "Refresh" })).toBeDisabled();
    expect(within(completedRow).getByRole("button", { name: "Refresh" })).toBeEnabled();
    expect(within(failedRow).getByRole("button", { name: "Refresh" })).toBeEnabled();
    expect(within(failedQueuedRow).getByRole("button", { name: "Refresh" })).toBeDisabled();
  });

  it("reprocesses a failed document from the detail page", async () => {
    window.localStorage.setItem(AUTH_ACCESS_TOKEN_STORAGE_KEY, "token");

    const failedStatus = {
      ...documentStatusResponse,
      latest_job: {
        ...documentStatusResponse.latest_job!,
        status: "failed" as const,
        visible_error_detail: "Expecting value: line 1 column 1 (char 0)"
      },
      processing_status: {
        ...documentStatusResponse.processing_status,
        detail: "Expecting value: line 1 column 1 (char 0)",
        extraction: "failed" as const,
        graph: "pending" as const,
        overall: "failed" as const
      }
    };
    const queuedStatus = {
      ...failedStatus,
      has_queued_reprocess: true,
      latest_job: {
        ...failedStatus.latest_job!,
        started_at: null,
        status: "queued" as const,
        visible_error_detail: null
      },
      queued_job_count: 1
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
            processing_status: currentStatus.processing_status
          });
        }
        if (url.includes(`/api/v1/ingestion/documents/${documentDetail.id}/reprocess`) && init?.method === "POST") {
          currentStatus = queuedStatus;
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

    await waitFor(() => expect(screen.getByText("Overall: Failed")).toBeInTheDocument());
    const processingErrorAlert = screen.getByText("Processing error").closest("[role='alert']");
    expect(processingErrorAlert).toHaveTextContent("Expecting value: line 1 column 1 (char 0)");

    const user = userEvent.setup();
    const reprocessButton = screen.getByRole("button", { name: "Reprocess document" });
    expect(reprocessButton).toBeEnabled();
    await user.click(reprocessButton);

    await waitFor(() => expect(screen.getByText("Overall: Queued")).toBeInTheDocument());
    expect(screen.getByText("Latest job: queued")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText("Processing error")).not.toBeInTheDocument());
    expect(screen.queryByText("Expecting value: line 1 column 1 (char 0)")).not.toBeInTheDocument();
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
            title: "New chat"
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
      active_job: {
        ...documentStatusResponse.latest_job!,
        completed_at: null,
        started_at: "2026-06-22T17:05:00Z",
        status: "processing" as const
      },
      chunk_count: 113,
      latest_job: {
        ...documentStatusResponse.latest_job!,
        completed_at: null,
        started_at: "2026-06-22T17:05:00Z",
        status: "processing" as const
      },
      processing_status: {
        ...documentStatusResponse.processing_status,
        extraction: "processing" as const,
        graph: "pending" as const,
        overall: "processing" as const,
        vector: "completed" as const
      }
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
            processing_status: processingStatus.processing_status
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
    expect(screen.getByText("Overall: Extracting")).toBeInTheDocument();
    expect(screen.getByText((content) => content.startsWith("Started:"))).toBeInTheDocument();
    expect(screen.getByText("Elapsed: 10m 30s")).toBeInTheDocument();
    expect(screen.getByText(/processed chunk-by-chunk locally/i)).toBeInTheDocument();
    expect(screen.getByText(/113 chunks/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reprocess document" })).toBeDisabled();
    expect(screen.queryByText("Processing error")).not.toBeInTheDocument();
    expect(screen.queryByText(/^Detail$/i)).not.toBeInTheDocument();
    expect(screen.queryByText("null")).not.toBeInTheDocument();
  });

  it("shows percent text immediately while a library refresh is starting", async () => {
    window.localStorage.setItem(AUTH_ACCESS_TOKEN_STORAGE_KEY, "token");

    const refreshDocument = {
      ...buildDocumentListItem("refreshing-document", "refreshing.pdf"),
      chunk_count: 12,
      indexed_chunk_count: 12
    };

    const completedStatus = {
      ...documentStatusResponse,
      chunk_count: 12,
      document_id: refreshDocument.id,
      indexed_chunk_count: 12,
      processing_status: refreshDocument.processing_status,
      queued_job_count: 0,
      queue_runtime: null
    };

    const queuedStatus = {
      ...completedStatus,
      has_queued_reprocess: true,
      latest_job: {
        ...documentStatusResponse.latest_job!,
        completed_at: null,
        requested_stage: "parsing",
        started_at: null,
        status: "queued" as const,
        visible_error_detail: null
      },
      processing_status: {
        ...documentDetail.processing_status,
        extraction: "pending" as const,
        graph: "pending" as const,
        overall: "pending" as const,
        parsing: "pending" as const,
        vector: "pending" as const
      },
      queued_job_count: 1,
      queue_runtime: {
        chunk_progress_current: 0,
        chunk_progress_total: 12,
        detail: null,
        enqueued_at: "2026-06-22T17:01:00Z",
        ended_at: null,
        job_id: documentStatusResponse.latest_job!.id,
        queue_job_id: documentStatusResponse.latest_job!.id,
        queue_name: "document-processing",
        queue_position: 1,
        stage: "parsing",
        started_at: null,
        status: "queued",
        updated_at: "2026-06-22T17:01:00Z",
        worker_name: null
      }
    };

    let currentStatus = completedStatus;
    let holdDocumentsRefetch: (() => void) | null = null;
    let shouldDelayNextDocumentsFetch = false;

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
        if (url.includes("/api/v1/ingestion/documents/status/batch") && init?.method === "POST") {
          return jsonResponse({
            statuses: [currentStatus]
          });
        }
        if (url.includes(`/api/v1/ingestion/documents/${refreshDocument.id}/reprocess`) && init?.method === "POST") {
          currentStatus = queuedStatus;
          shouldDelayNextDocumentsFetch = true;
          return jsonResponse(currentStatus);
        }
        if (url.includes("/api/v1/documents") && (!init?.method || init.method === "GET")) {
          if (shouldDelayNextDocumentsFetch) {
            shouldDelayNextDocumentsFetch = false;
            return new Promise<Response>((resolve) => {
              holdDocumentsRefetch = () =>
                resolve(
                  jsonResponse({
                    ...documentListResponse,
                    items: [refreshDocument],
                    total: 1
                  })
                );
            });
          }
          return jsonResponse({
            ...documentListResponse,
            items: [refreshDocument],
            total: 1
          });
        }
        return jsonResponse({}, { status: 404 });
      })
    );

    render(
      <MemoryRouter initialEntries={["/documents"]}>
        <AppProviders>
          <Routes>
            <Route path="/documents" element={<DocumentsPage />} />
          </Routes>
        </AppProviders>
      </MemoryRouter>
    );

    await waitFor(() => expect(screen.getByText("refreshing.pdf")).toBeInTheDocument());

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Refresh" }));

    const refreshRow = screen.getByText("refreshing.pdf").closest("tr")!;
    await waitFor(() => expect(within(refreshRow).getByText("Refreshing…")).toBeInTheDocument());
    expect(within(refreshRow).getByText("Parsing")).toBeInTheDocument();
    expect(within(refreshRow).getByText("0%")).toBeInTheDocument();
    expect(within(refreshRow).queryByText("0/48 items")).not.toBeInTheDocument();
    expectProgressState(refreshRow, "Parsing chunk progress", "0", "bg-sky-600");

    holdDocumentsRefetch?.();
    await waitFor(() => expect(within(refreshRow).getByText("Refresh")).toBeInTheDocument());
  });
});
