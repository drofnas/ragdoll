import type { ProcessingStageStatus } from "@contracts";
import { useEffect, useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  Code,
  Group,
  Select,
  SimpleGrid,
  Stack,
  Text,
  Title
} from "@mantine/core";
import { useQuery } from "@tanstack/react-query";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";

import { ApiProblemError } from "../../../shared/api/client";
import { triggerBrowserDownload } from "../../../shared/lib/downloads";
import { formatDateTime, formatFileSize, humanizeStageStatus } from "../../../shared/lib/formatting";
import { useSpaceScope } from "../../../shared/state/spaceScope";
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
  const [moveTarget, setMoveTarget] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [isMoving, setIsMoving] = useState(false);
  const [isReprocessing, setIsReprocessing] = useState(false);

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

  return (
    <Stack gap="xl">
      <Group justify="space-between" align="end">
        <Stack gap={4}>
          <Button component={Link} to="/documents" variant="subtle">
            Back to library
          </Button>
          <Title order={2}>{detailQuery.data?.title ?? "Document detail"}</Title>
          <Text c="dimmed">{detailQuery.data?.original_filename}</Text>
        </Stack>
        {statusQuery.data ? <Badge variant="light">{humanizeStageStatus(statusQuery.data.processing_status.overall)}</Badge> : null}
      </Group>

      {errorMessage ? (
        <Alert color="red" title="Document action failed">
          {errorMessage}
        </Alert>
      ) : null}

      {detailQuery.isLoading ? (
        <Text c="dimmed">Loading document detail…</Text>
      ) : detailQuery.error instanceof ApiProblemError ? (
        <Alert color="red" title="Unable to load document">
          {detailQuery.error.problem.detail}
        </Alert>
      ) : detailQuery.data ? (
        <>
          <SimpleGrid cols={{ base: 1, lg: 3 }}>
            <Card withBorder radius="lg" p="lg">
              <Stack gap="xs">
                <Title order={4}>Metadata</Title>
                <Text>{formatFileSize(detailQuery.data.file_size)}</Text>
                <Text>{detailQuery.data.file_type.toUpperCase()}</Text>
                <Text>Uploaded {formatDateTime(detailQuery.data.created_at)}</Text>
                <Text>Updated {formatDateTime(detailQuery.data.updated_at)}</Text>
              </Stack>
            </Card>

            <Card withBorder radius="lg" p="lg">
              <Stack gap="md">
                <Title order={4}>Processing</Title>
                {statusQuery.data ? (
                  <>
                    <Text>Overall: {humanizeStageStatus(statusQuery.data.processing_status.overall)}</Text>
                    <Text>Chunks: {statusQuery.data.chunk_count}</Text>
                    <Text>Indexed chunks: {statusQuery.data.indexed_chunk_count}</Text>
                    <Text>Latest job: {statusQuery.data.latest_job?.status ?? "Not yet queued"}</Text>
                    <Button
                      loading={isReprocessing}
                      variant="light"
                      onClick={() => void handleReprocessDocument()}
                    >
                      Reprocess document
                    </Button>
                  </>
                ) : (
                  <Text c="dimmed">Waiting for live status…</Text>
                )}
              </Stack>
            </Card>

            <Card withBorder radius="lg" p="lg">
              <Stack gap="md">
                <Title order={4}>Actions</Title>
                <Button loading={isDownloading} onClick={() => void handleDownloadDocument()}>
                  Download original
                </Button>
                <Select
                  data={spaces
                    .filter((space) => space.id !== detailQuery.data.space_id)
                    .map((space) => ({ label: space.name, value: space.id }))}
                  label="Move to Space"
                  placeholder="Choose a Space"
                  value={moveTarget}
                  onChange={setMoveTarget}
                />
                <Button loading={isMoving} variant="light" onClick={() => void handleMoveDocument()}>
                  Move document
                </Button>
                <Button color="red" loading={isDeleting} variant="light" onClick={() => void handleDeleteDocument()}>
                  Delete document
                </Button>
              </Stack>
            </Card>
          </SimpleGrid>

          <Card withBorder radius="lg" p="lg">
            <Stack gap="md">
              <Title order={4}>Stage detail</Title>
              {statusQuery.data ? (
                <SimpleGrid cols={{ base: 2, md: 3 }}>
                  {Object.entries(statusQuery.data.processing_status).map(([key, value]) => (
                    <Card key={key} withBorder radius="md" p="sm">
                      <Stack gap={2}>
                        <Text fw={600} tt="capitalize">
                          {key.replace(/_/g, " ")}
                        </Text>
                        <Badge variant="light">{typeof value === "string" ? humanizeStageStatus(value) : String(value)}</Badge>
                      </Stack>
                    </Card>
                  ))}
                </SimpleGrid>
              ) : (
                <Text c="dimmed">Status is still loading.</Text>
              )}
            </Stack>
          </Card>

          <SimpleGrid cols={{ base: 1, lg: 2 }}>
            <Card withBorder radius="lg" p="lg">
              <Stack gap="md">
                <Title order={4}>Preview text</Title>
                <Text style={{ whiteSpace: "pre-wrap" }}>
                  {detailQuery.data.preview_text || "No preview text is available yet."}
                </Text>
              </Stack>
            </Card>
            <Card withBorder radius="lg" p="lg">
              <Stack gap="md">
                <Title order={4}>Original extracted text</Title>
                <Code block>{detailQuery.data.original_text_content || "Extraction has not populated full text yet."}</Code>
              </Stack>
            </Card>
          </SimpleGrid>
        </>
      ) : null}
    </Stack>
  );
}
