import type { ProcessingStageStatus } from "@contracts";
import { useEffect, useState } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { Page, PageHeader } from "@/components/app/page";
import { SelectField } from "@/components/app/select-field";
import { StatusBadge } from "@/components/app/status-badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ApiProblemError } from "@/shared/api/client";
import { triggerBrowserDownload } from "@/shared/lib/downloads";
import {
  formatDateTime,
  formatElapsedDuration,
  formatFileSize,
  humanizeStageStatus
} from "@/shared/lib/formatting";
import { useSpaceScope } from "@/shared/state/spaceScope";
import { createChatSession } from "../../chat/api/chatApi";
import {
  deleteDocument,
  downloadDocument,
  moveDocument,
  readDocument,
  readDocumentStatus,
  reprocessDocument
} from "../api/documentsApi";

const TERMINAL_STATUSES: ProcessingStageStatus[] = ["completed", "deferred", "failed"];

export function DocumentDetailPage() {
  const navigate = useNavigate();
  const { documentId } = useParams<{ documentId: string }>();
  const { spaces } = useSpaceScope();
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [moveTarget, setMoveTarget] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [isMoving, setIsMoving] = useState(false);
  const [isReprocessing, setIsReprocessing] = useState(false);
  const [isStartingChat, setIsStartingChat] = useState(false);

  const detailQuery = useQuery({
    enabled: Boolean(documentId),
    queryFn: () => readDocument(documentId!),
    queryKey: ["document", documentId],
    refetchInterval: (query) => {
      const overall = query.state.data?.processing_status.overall;
      return overall && !TERMINAL_STATUSES.includes(overall) ? 3000 : false;
    }
  });

  const statusQuery = useQuery({
    enabled: Boolean(documentId),
    queryFn: () => readDocumentStatus(documentId!),
    queryKey: ["document-status", documentId],
    refetchInterval: (query) => {
      const overall = query.state.data?.processing_status.overall;
      return overall && !TERMINAL_STATUSES.includes(overall) ? 3000 : false;
    }
  });

  const latestJob = statusQuery.data?.latest_job;
  const extractionIsActive = statusQuery.data?.processing_status.extraction === "processing";
  const isProcessing = Boolean(
    statusQuery.data && !TERMINAL_STATUSES.includes(statusQuery.data.processing_status.overall)
  );
  const extractionHint = statusQuery.data?.chunk_count
    ? `Large documents are processed chunk-by-chunk locally and may take tens of minutes. This document currently has ${statusQuery.data.chunk_count} chunks.`
    : "Large documents are processed chunk-by-chunk locally and may take tens of minutes.";

  useEffect(() => {
    if (!detailQuery.data) {
      return;
    }
    setMoveTarget(detailQuery.data.space_id);
  }, [detailQuery.data]);

  if (!documentId) {
    return <Navigate to="/documents" replace />;
  }

  async function handleMoveDocument() {
    if (!moveTarget || moveTarget === detailQuery.data?.space_id) {
      return;
    }

    setIsMoving(true);
    setErrorMessage(null);
    try {
      await moveDocument(documentId, { space_id: moveTarget });
      await detailQuery.refetch();
    } catch (error) {
      if (error instanceof ApiProblemError) {
        setErrorMessage(error.problem.detail);
      } else {
        setErrorMessage("Unable to move the document right now.");
      }
    } finally {
      setIsMoving(false);
    }
  }

  async function handleDeleteDocument() {
    setIsDeleting(true);
    setErrorMessage(null);
    try {
      await deleteDocument(documentId);
      navigate("/documents", { replace: true });
    } catch (error) {
      if (error instanceof ApiProblemError) {
        setErrorMessage(error.problem.detail);
      } else {
        setErrorMessage("Unable to delete the document right now.");
      }
      setIsDeleting(false);
    }
  }

  async function handleDownloadDocument() {
    setIsDownloading(true);
    setErrorMessage(null);
    try {
      const blob = await downloadDocument(documentId);
      triggerBrowserDownload(blob, detailQuery.data?.original_filename ?? "document");
    } catch (error) {
      if (error instanceof ApiProblemError) {
        setErrorMessage(error.problem.detail);
      } else {
        setErrorMessage("Unable to download the document right now.");
      }
    } finally {
      setIsDownloading(false);
    }
  }

  async function handleReprocessDocument() {
    setIsReprocessing(true);
    setErrorMessage(null);
    try {
      await reprocessDocument(documentId);
      await Promise.all([detailQuery.refetch(), statusQuery.refetch()]);
    } catch (error) {
      if (error instanceof ApiProblemError) {
        setErrorMessage(error.problem.detail);
      } else {
        setErrorMessage("Unable to reprocess the document right now.");
      }
    } finally {
      setIsReprocessing(false);
    }
  }

  async function handleStartDocumentChat() {
    if (!detailQuery.data) {
      return;
    }

    setIsStartingChat(true);
    setErrorMessage(null);
    try {
      const session = await createChatSession({
        space_id: detailQuery.data.space_id,
        document_id: detailQuery.data.id
      });
      navigate(`/chat/${session.id}`);
    } catch (error) {
      if (error instanceof ApiProblemError) {
        setErrorMessage(error.problem.detail);
      } else {
        setErrorMessage("Unable to start a chat for this document right now.");
      }
    } finally {
      setIsStartingChat(false);
    }
  }

  return (
    <Page>
      <PageHeader
        eyebrow="Document detail"
        title={detailQuery.data?.title ?? "Document detail"}
        description={detailQuery.data?.original_filename}
        actions={statusQuery.data ? <StatusBadge value={statusQuery.data.processing_status.overall} label={humanizeStageStatus(statusQuery.data.processing_status.overall)} /> : undefined}
      >
        <div>
          <Button asChild variant="ghost">
            <Link to="/documents">Back to library</Link>
          </Button>
        </div>
      </PageHeader>

      {errorMessage ? (
        <Alert variant="destructive">
          <AlertTitle>Document action failed</AlertTitle>
          <AlertDescription>{errorMessage}</AlertDescription>
        </Alert>
      ) : null}

      {detailQuery.isLoading ? (
        <p className="text-sm text-muted-foreground">Loading document detail…</p>
      ) : detailQuery.error instanceof ApiProblemError ? (
        <Alert variant="destructive">
          <AlertTitle>Unable to load document</AlertTitle>
          <AlertDescription>{detailQuery.error.problem.detail}</AlertDescription>
        </Alert>
      ) : detailQuery.data ? (
        <>
          <section className="grid gap-4 lg:grid-cols-3">
            <Card>
              <CardHeader>
                <CardTitle>Metadata</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <p>{formatFileSize(detailQuery.data.file_size)}</p>
                <p>{detailQuery.data.file_type.toUpperCase()}</p>
                <p>Uploaded {formatDateTime(detailQuery.data.created_at)}</p>
                <p>Updated {formatDateTime(detailQuery.data.updated_at)}</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Processing</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                {statusQuery.data ? (
                  <>
                    <p>
                      Overall: {humanizeStageStatus(statusQuery.data.processing_status.overall)}
                    </p>
                    <p>Chunks: {statusQuery.data.chunk_count}</p>
                    <p>Indexed chunks: {statusQuery.data.indexed_chunk_count}</p>
                    <p>Latest job: {statusQuery.data.latest_job?.status ?? "Not yet queued"}</p>
                    <p>Started: {formatDateTime(latestJob?.started_at)}</p>
                    {isProcessing && latestJob?.started_at ? (
                      <p>Elapsed: {formatElapsedDuration(latestJob.started_at)}</p>
                    ) : null}
                    {extractionIsActive ? (
                      <Alert variant="info">
                        <AlertTitle>Extraction is still running</AlertTitle>
                        <AlertDescription>{extractionHint}</AlertDescription>
                      </Alert>
                    ) : null}
                    <Button variant="outline" onClick={() => void handleReprocessDocument()}>
                      {isReprocessing ? "Reprocessing…" : "Reprocess document"}
                    </Button>
                  </>
                ) : (
                  <p className="text-muted-foreground">Waiting for live status…</p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Actions</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <Button className="w-full" onClick={() => void handleDownloadDocument()}>
                  {isDownloading ? "Downloading…" : "Download original"}
                </Button>
                <Button className="w-full" variant="outline" onClick={() => void handleStartDocumentChat()}>
                  {isStartingChat ? "Starting chat…" : "Chat about this document"}
                </Button>
                {moveTarget ? (
                  <SelectField
                    label="Move to Space"
                    options={spaces.map((space) => ({ label: space.name, value: space.id }))}
                    placeholder="Choose a Space"
                    value={moveTarget}
                    onValueChange={setMoveTarget}
                  />
                ) : (
                  <div className="space-y-2">
                    <p className="text-sm font-medium">Move to Space</p>
                    <p className="rounded-md border bg-muted/20 px-3 py-2 text-sm text-muted-foreground">
                      Loading available Spaces…
                    </p>
                  </div>
                )}
                <Button
                  className="w-full"
                  variant="outline"
                  disabled={!moveTarget || moveTarget === detailQuery.data.space_id}
                  onClick={() => void handleMoveDocument()}
                >
                  {isMoving ? "Moving…" : "Move document"}
                </Button>
                <Button className="w-full" variant="destructive" onClick={() => void handleDeleteDocument()}>
                  {isDeleting ? "Deleting…" : "Delete document"}
                </Button>
              </CardContent>
            </Card>
          </section>

          <Card>
            <CardHeader>
              <CardTitle>Stage detail</CardTitle>
            </CardHeader>
            <CardContent>
              {statusQuery.data ? (
                <div className="grid gap-3 md:grid-cols-3">
                  {Object.entries(statusQuery.data.processing_status).map(([key, value]) => (
                    <Card key={key} className="bg-background/65 shadow-none">
                      <CardContent className="space-y-2 p-5">
                        <p className="text-sm font-semibold capitalize">{key.replace(/_/g, " ")}</p>
                        <StatusBadge
                          value={typeof value === "string" ? value : String(value)}
                          label={
                            typeof value === "string"
                              ? humanizeStageStatus(value)
                              : String(value)
                          }
                        />
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">Status is still loading.</p>
              )}
            </CardContent>
          </Card>

          <section className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Preview text</CardTitle>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[28rem] rounded-md border bg-muted/20 p-4">
                  <p className="whitespace-pre-wrap text-sm leading-7">
                    {detailQuery.data.preview_text || "No preview text is available yet."}
                  </p>
                </ScrollArea>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Original extracted text</CardTitle>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[28rem] rounded-md border bg-slate-950 p-4">
                  <pre className="whitespace-pre-wrap text-sm leading-7 text-slate-100">
                    {detailQuery.data.original_text_content ||
                      "Extraction has not populated full text yet."}
                  </pre>
                </ScrollArea>
              </CardContent>
            </Card>
          </section>
        </>
      ) : null}
    </Page>
  );
}
