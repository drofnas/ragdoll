import type { ProcessingStageStatus } from "@contracts";
import { useState, type FormEvent } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  Group,
  Pagination,
  Select,
  SimpleGrid,
  Stack,
  Text,
  Title
} from "@mantine/core";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";

import { ApiProblemError } from "../../../shared/api/client";
import { formatDateTime, formatFileSize, humanizeStageStatus } from "../../../shared/lib/formatting";
import { useSpaceScope } from "../../../shared/state/spaceScope";
import { listDocuments, uploadDocument, type ListDocumentsQuery } from "../api/documentsApi";

const TERMINAL_STATUSES: ProcessingStageStatus[] = ["completed", "deferred", "failed"];

export function DocumentsPage() {
  const navigate = useNavigate();
  const { activeSpace, allSpaces, buildReadScopeParams, isReady, requireConcreteSpace } = useSpaceScope();
  const [page, setPage] = useState(1);
  const [fileTypeFilter, setFileTypeFilter] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

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
      return items.some((item) => !TERMINAL_STATUSES.includes(item.processing_status.overall)) ? 3000 : false;
    }
  });

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage(null);

    if (!file) {
      setErrorMessage("Choose a file before uploading.");
      return;
    }

    let concreteSpaceId: string;
    try {
      concreteSpaceId = requireConcreteSpace().id;
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Choose one Space before uploading.");
      return;
    }

    setIsUploading(true);
    try {
      const response = await uploadDocument(file, { space_id: concreteSpaceId });
      navigate(`/documents/${response.document_id}`);
    } catch (error) {
      if (error instanceof ApiProblemError) {
        setErrorMessage(error.problem.detail);
      } else {
        setErrorMessage("Unable to upload the document right now.");
      }
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <Stack gap="xl">
      <Stack gap={4}>
        <Title order={2}>Documents</Title>
        <Text c="dimmed">
          Upload files, track processing progress, and move between Spaces without leaving the workspace.
        </Text>
      </Stack>

      {allSpaces ? (
        <Alert color="blue" title="Read scope spans all Spaces">
          Upload is disabled until you choose one active Space in the shell selector.
        </Alert>
      ) : null}

      {errorMessage ? (
        <Alert color="red" title="Document action failed">
          {errorMessage}
        </Alert>
      ) : null}

      <SimpleGrid cols={{ base: 1, lg: 2 }}>
        <Card withBorder radius="lg" p="lg">
          <Stack gap="md">
            <Title order={4}>Upload a document</Title>
            <Text c="dimmed" size="sm">
              Current target: {activeSpace?.name ?? "Choose a Space first"}
            </Text>
            <form onSubmit={handleUpload}>
              <Stack gap="md">
                <input
                  accept=".pdf,.docx,.txt,.md,.markdown"
                  disabled={isUploading || allSpaces}
                  type="file"
                  onChange={(event) => setFile(event.currentTarget.files?.[0] ?? null)}
                />
                <Button disabled={allSpaces} loading={isUploading} type="submit">
                  Upload
                </Button>
              </Stack>
            </form>
          </Stack>
        </Card>

        <Card withBorder radius="lg" p="lg">
          <Stack gap="md">
            <Title order={4}>Filter the library</Title>
            <Select
              clearable
              data={[
                { label: "PDF", value: "pdf" },
                { label: "DOCX", value: "docx" },
                { label: "Markdown", value: "md" },
                { label: "Text", value: "txt" }
              ]}
              label="File type"
              placeholder="All file types"
              value={fileTypeFilter}
              onChange={(value) => {
                setPage(1);
                setFileTypeFilter(value);
              }}
            />
            <Text c="dimmed" size="sm">
              Scope-aware reads respect the active Space unless the all-spaces toggle is enabled.
            </Text>
          </Stack>
        </Card>
      </SimpleGrid>

      <Stack gap="md">
        <Group justify="space-between">
          <Title order={3}>Library</Title>
          <Badge variant="light">{documentsQuery.data?.total ?? 0} documents</Badge>
        </Group>

        {documentsQuery.isLoading ? (
          <Text c="dimmed">Loading documents…</Text>
        ) : documentsQuery.error instanceof ApiProblemError ? (
          <Alert color="red" title="Unable to load documents">
            {documentsQuery.error.problem.detail}
          </Alert>
        ) : documentsQuery.data && documentsQuery.data.items.length > 0 ? (
          <>
            <SimpleGrid cols={{ base: 1, md: 2 }}>
              {documentsQuery.data.items.map((document) => (
                <Card key={document.id} withBorder radius="lg" p="lg">
                  <Stack gap="md">
                    <Group justify="space-between" align="start">
                      <Stack gap={2}>
                        <Title order={4}>{document.title}</Title>
                        <Text c="dimmed" size="sm">
                          {document.original_filename}
                        </Text>
                      </Stack>
                      <Badge variant="light">{humanizeStageStatus(document.processing_status.overall)}</Badge>
                    </Group>

                    <Text size="sm">
                      {formatFileSize(document.file_size)} · {document.file_type.toUpperCase()} · {document.chunk_count} chunks
                    </Text>
                    <Text size="sm">Updated {formatDateTime(document.updated_at)}</Text>

                    <Button component={Link} to={`/documents/${document.id}`} variant="light">
                      Open detail
                    </Button>
                  </Stack>
                </Card>
              ))}
            </SimpleGrid>
            <Group justify="center">
              <Pagination
                total={Math.max(1, Math.ceil(documentsQuery.data.total / documentsQuery.data.page_size))}
                value={page}
                onChange={setPage}
              />
            </Group>
          </>
        ) : (
          <Text c="dimmed">No documents match the current scope and filter yet.</Text>
        )}
      </Stack>
    </Stack>
  );
}
