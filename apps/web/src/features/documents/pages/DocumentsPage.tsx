import type { ProcessingStageStatus } from "@contracts";
import { Eye, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { Page, PageHeader } from "@/components/app/page";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle
} from "@/components/ui/dialog";
import { Pagination } from "@/components/ui/pagination";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from "@/components/ui/table";
import { ApiProblemError } from "@/shared/api/client";
import { formatDateTime, formatFileSize } from "@/shared/lib/formatting";
import { useSpaceScope } from "@/shared/state/spaceScope";
import {
  listDocuments,
  readBatchDocumentStatuses,
  reprocessDocument,
  uploadDocument,
  type ListDocumentsQuery
} from "../api/documentsApi";
import {
  DocumentUploadDropzone,
  type DocumentUploadQueueItem
} from "../components/DocumentUploadDropzone";
import {
  buildStatusMap,
  getDocumentChunkStatusPresentation,
  hasInFlightDocumentWork,
  isRefreshLocked
} from "../lib/documentStatus";

const TERMINAL_STATUSES: ProcessingStageStatus[] = ["completed", "deferred", "failed"];

const fileTypeOptions = [
  { label: "All file types", value: "__all__" },
  { label: "PDF", value: "pdf" },
  { label: "DOCX", value: "docx" },
  { label: "Markdown", value: "md" },
  { label: "Text", value: "txt" }
];

const chunkProgressIndicatorClassNames = {
  completed: "bg-primary",
  failed: "bg-destructive",
  idle: "bg-muted-foreground/30",
  processing: "bg-sky-600"
};

function createUploadQueueItem(file: File, spaceId: string): DocumentUploadQueueItem {
  return {
    file,
    id: `${file.name}-${file.size}-${file.lastModified}-${Math.random().toString(36).slice(2)}`,
    spaceId,
    status: "queued"
  };
}

export function DocumentsPage() {
  const queryClient = useQueryClient();
  const { activeSpace, allSpaces, buildReadScopeParams, isReady, requireConcreteSpace } = useSpaceScope();
  const [page, setPage] = useState(1);
  const [fileTypeFilter, setFileTypeFilter] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isUploadDialogOpen, setIsUploadDialogOpen] = useState(false);
  const [forceLibraryPolling, setForceLibraryPolling] = useState(false);
  const [uploadItems, setUploadItems] = useState<DocumentUploadQueueItem[]>([]);
  const [refreshingDocumentIds, setRefreshingDocumentIds] = useState<string[]>([]);

  const scopeQuery = buildReadScopeParams();
  const documentQuery: ListDocumentsQuery = {
    page,
    page_size: 12,
    file_type: fileTypeFilter || undefined,
    ...scopeQuery
  };

  const documentsQuery = useQuery({
    enabled: isReady,
    queryFn: () => listDocuments(documentQuery),
    queryKey: ["documents", documentQuery],
    refetchInterval: (query) => {
      const items = query.state.data?.items ?? [];
      return forceLibraryPolling ||
        items.some((item) => !TERMINAL_STATUSES.includes(item.processing_status.overall))
        ? 3000
        : false;
    }
  });

  const visibleDocumentIds = documentsQuery.data?.items.map((document) => document.id) ?? [];
  const documentStatusesQuery = useQuery({
    enabled: isReady && visibleDocumentIds.length > 0,
    queryFn: () => readBatchDocumentStatuses({ document_ids: visibleDocumentIds }),
    queryKey: ["document-statuses", visibleDocumentIds],
    refetchInterval: (query) => {
      const statuses = query.state.data?.statuses ?? [];
      return forceLibraryPolling || statuses.some((status) => hasInFlightDocumentWork(status))
        ? 3000
        : false;
    }
  });

  const liveStatusById = buildStatusMap(documentStatusesQuery.data?.statuses);

  useEffect(() => {
    if (!forceLibraryPolling) {
      return;
    }

    const documentsNeedPolling = (documentsQuery.data?.items ?? []).some(
      (item) => !TERMINAL_STATUSES.includes(item.processing_status.overall)
    );
    const statusesNeedPolling = (documentStatusesQuery.data?.statuses ?? []).some((status) =>
      hasInFlightDocumentWork(status)
    );

    if (!documentsNeedPolling && !statusesNeedPolling && !isUploading) {
      setForceLibraryPolling(false);
    }
  }, [
    documentStatusesQuery.data?.statuses,
    documentsQuery.data?.items,
    forceLibraryPolling,
    isUploading
  ]);

  useEffect(() => {
    if (isUploading) {
      return;
    }

    const nextItem = uploadItems.find((item) => item.status === "queued");
    if (!nextItem) {
      return;
    }

    setIsUploading(true);
    setUploadItems((items) =>
      items.map((item) => (item.id === nextItem.id ? { ...item, status: "uploading" } : item))
    );

    void (async () => {
      try {
        await uploadDocument(nextItem.file, { space_id: nextItem.spaceId });
        setForceLibraryPolling(true);
        setUploadItems((items) =>
          items.map((item) =>
            item.id === nextItem.id
              ? { ...item, errorMessage: undefined, status: "completed" }
              : item
          )
        );
        await queryClient.invalidateQueries({ queryKey: ["documents"] });
        await queryClient.invalidateQueries({ queryKey: ["document-statuses"] });
      } catch (error) {
        const message =
          error instanceof ApiProblemError
            ? error.problem.detail
            : "Unable to upload the document right now.";
        setErrorMessage(message);
        setUploadItems((items) =>
          items.map((item) =>
            item.id === nextItem.id ? { ...item, errorMessage: message, status: "failed" } : item
          )
        );
      } finally {
        setIsUploading(false);
      }
    })();
  }, [isUploading, queryClient, uploadItems]);

  function handleFilesSelected(files: File[]) {
    let concreteSpaceId: string;
    try {
      concreteSpaceId = requireConcreteSpace().id;
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "Choose one Space before uploading."
      );
      return;
    }

    setErrorMessage(null);
    setPage(1);
    setForceLibraryPolling(true);
    setUploadItems((items) => [
      ...items,
      ...files.map((file) => createUploadQueueItem(file, concreteSpaceId))
    ]);
  }

  function handleRemoveUploadItem(itemId: string) {
    setUploadItems((items) => items.filter((item) => item.id !== itemId));
  }

  async function handleRefreshDocument(documentId: string) {
    setErrorMessage(null);
    setForceLibraryPolling(true);
    setRefreshingDocumentIds((documentIds) => [...documentIds, documentId]);

    try {
      await reprocessDocument(documentId);
      await Promise.all([
        documentsQuery.refetch(),
        queryClient.invalidateQueries({ queryKey: ["document-statuses"] })
      ]);
    } catch (error) {
      if (error instanceof ApiProblemError) {
        setErrorMessage(error.problem.detail);
      } else {
        setErrorMessage("Unable to refresh the document right now.");
      }
    } finally {
      setRefreshingDocumentIds((documentIds) =>
        documentIds.filter((currentDocumentId) => currentDocumentId !== documentId)
      );
    }
  }

  return (
    <Page>
      <PageHeader
        eyebrow="Library"
        title="Documents"
        description="Upload files, track processing progress, and move between Spaces without leaving the workspace."
      />

      {allSpaces ? (
        <Alert variant="info">
          <AlertTitle>Read scope spans all Spaces</AlertTitle>
          <AlertDescription>
            Upload is disabled until you choose one active Space in the shell selector.
          </AlertDescription>
        </Alert>
      ) : null}

      {errorMessage ? (
        <Alert variant="destructive">
          <AlertTitle>Document action failed</AlertTitle>
          <AlertDescription>{errorMessage}</AlertDescription>
        </Alert>
      ) : null}

      <Dialog open={isUploadDialogOpen} onOpenChange={setIsUploadDialogOpen}>
        <DialogContent className="max-h-[85vh] max-w-4xl overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Upload documents</DialogTitle>
            <DialogDescription>
              Upload files, track processing progress, and move between Spaces without leaving the
              workspace.
            </DialogDescription>
          </DialogHeader>
          <DocumentUploadDropzone
            disabled={Boolean(allSpaces)}
            disabledCopy="Choose one active Space in the shell selector to enable uploads."
            isUploading={isUploading}
            items={uploadItems}
            targetLabel={activeSpace?.name ?? "Choose a Space first"}
            onFilesSelected={handleFilesSelected}
            onRemoveItem={handleRemoveUploadItem}
          />
        </DialogContent>
      </Dialog>

      <section className="space-y-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-3">
            <h2 className="text-2xl font-semibold tracking-tight">Library</h2>
            <Badge variant="outline">{documentsQuery.data?.total ?? 0} documents</Badge>
          </div>
          <div className="flex flex-col gap-3 md:flex-row md:items-center">
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Filter</span>
              <Select
                value={fileTypeFilter ?? "__all__"}
                onValueChange={(value) => {
                  setPage(1);
                  setFileTypeFilter(value === "__all__" ? null : value);
                }}
              >
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="All file types" />
                </SelectTrigger>
                <SelectContent>
                  {fileTypeOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button type="button" onClick={() => setIsUploadDialogOpen(true)}>
              Upload
            </Button>
          </div>
        </div>

        {documentsQuery.isLoading ? (
          <p className="text-sm text-muted-foreground">Loading documents…</p>
        ) : documentsQuery.error instanceof ApiProblemError ? (
          <Alert variant="destructive">
            <AlertTitle>Unable to load documents</AlertTitle>
            <AlertDescription>{documentsQuery.error.problem.detail}</AlertDescription>
          </Alert>
        ) : documentsQuery.data && documentsQuery.data.items.length > 0 ? (
          <>
            <Card>
              <CardContent className="p-0">
                <Table className="table-fixed">
                  <TableHeader>
                    <TableRow>
                      <TableHead>Filename</TableHead>
                      <TableHead className="w-20">Type</TableHead>
                      <TableHead className="w-24">Size</TableHead>
                      <TableHead className="w-52">Chunk Status</TableHead>
                      <TableHead className="w-36">Updated</TableHead>
                      <TableHead className="w-52 text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {documentsQuery.data.items.map((document) => {
                      const liveStatus = liveStatusById.get(document.id);
                      const isRefreshingDocument = refreshingDocumentIds.includes(document.id);
                      const fallbackStatus = {
                        chunk_count: document.chunk_count,
                        indexed_chunk_count: document.indexed_chunk_count,
                        processing_status: document.processing_status,
                        queued_job_count: document.processing_status.overall === "pending" ? 1 : 0
                      };
                      const statusSource = liveStatus ?? fallbackStatus;
                      const chunkStatusSource = isRefreshingDocument
                        ? {
                            ...statusSource,
                            indexed_chunk_count: 0,
                            queue_runtime: {
                              ...statusSource.queue_runtime,
                              chunk_progress_current: 0,
                              chunk_progress_total: statusSource.chunk_count,
                              queue_position: null,
                              stage: "parsing",
                              status: "started"
                            },
                            processing_status: {
                              ...statusSource.processing_status,
                              extraction: "pending" as const,
                              graph: "pending" as const,
                              overall: "processing" as const,
                              parsing: "processing" as const,
                              vector: "pending" as const
                            }
                          }
                        : statusSource;
                      const chunkStatusPresentation = getDocumentChunkStatusPresentation(
                        chunkStatusSource
                      );
                      const refreshDisabled = Boolean(
                        isRefreshingDocument ||
                          isRefreshLocked(statusSource)
                      );

                      return (
                        <TableRow key={document.id}>
                          <TableCell className="max-w-0">
                            <span className="block truncate font-medium" title={document.original_filename}>
                              {document.original_filename}
                            </span>
                          </TableCell>
                          <TableCell>{document.file_type.toUpperCase()}</TableCell>
                          <TableCell>{formatFileSize(document.file_size)}</TableCell>
                          <TableCell>
                            <div className="w-full max-w-48 space-y-2">
                              <div className="flex items-center justify-between gap-3 text-sm">
                                <span className="font-medium">{chunkStatusPresentation.label}</span>
                                <span className="tabular-nums text-muted-foreground">
                                  {chunkStatusPresentation.valueLabel}
                                </span>
                              </div>
                              <Progress
                                aria-label={`${chunkStatusPresentation.label} chunk progress`}
                                indicatorClassName={
                                  chunkProgressIndicatorClassNames[
                                    chunkStatusPresentation.progressTone
                                  ]
                                }
                                value={chunkStatusPresentation.progressValue}
                              />
                            </div>
                          </TableCell>
                          <TableCell className="text-muted-foreground">
                            {formatDateTime(document.updated_at)}
                          </TableCell>
                          <TableCell>
                            <div className="flex justify-end gap-2">
                              <Button
                                size="sm"
                                variant="outline"
                                disabled={refreshDisabled}
                                onClick={() => void handleRefreshDocument(document.id)}
                              >
                                <RefreshCw aria-hidden="true" />
                                {refreshingDocumentIds.includes(document.id) ? "Refreshing…" : "Refresh"}
                              </Button>
                              <Button asChild size="sm" variant="outline">
                                <Link to={`/documents/${document.id}`}>
                                  <Eye aria-hidden="true" />
                                  View
                                </Link>
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
            <Pagination
              currentPage={page}
              totalPages={Math.max(
                1,
                Math.ceil(documentsQuery.data.total / documentsQuery.data.page_size)
              )}
              onPageChange={setPage}
            />
          </>
        ) : (
          <p className="text-sm text-muted-foreground">
            No documents match the current scope and filter yet.
          </p>
        )}
      </section>
    </Page>
  );
}
