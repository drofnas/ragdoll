import type { SearchMode } from "@contracts";
import { useEffect, useState, type FormEvent } from "react";
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
  TextInput,
  Title
} from "@mantine/core";
import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";

import { ApiProblemError } from "../../../shared/api/client";
import {
  formatCitationLabel,
  formatScore,
  formatSearchMode,
  formatSourceTier
} from "../../../shared/lib/formatting";
import { useSpaceScope } from "../../../shared/state/spaceScope";
import { readSearchResults, type SearchQuery } from "../api/searchApi";

const SEARCH_MODE_OPTIONS: Array<{ label: string; value: SearchMode }> = [
  { label: "Combined", value: "combined" },
  { label: "Boolean", value: "boolean" },
  { label: "Vector", value: "vector" },
  { label: "Graph", value: "graph" }
];

const FILE_TYPE_OPTIONS = [
  { label: "PDF", value: "pdf" },
  { label: "DOCX", value: "docx" },
  { label: "Markdown", value: "md" },
  { label: "Text", value: "txt" }
];

export function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { activeSpace, allSpaces, buildReadScopeParams, isReady } = useSpaceScope();
  const [queryText, setQueryText] = useState(searchParams.get("q") ?? "");
  const [documentIdInput, setDocumentIdInput] = useState(searchParams.get("document_id") ?? "");
  const [entityTypeInput, setEntityTypeInput] = useState(searchParams.get("entity_type") ?? "");

  const queryTextParam = searchParams.get("q")?.trim() ?? "";
  const fileTypeParam = searchParams.get("file_type") ?? "";
  const modeParam = (searchParams.get("mode") as SearchMode | null) ?? "combined";
  const documentIdParam = searchParams.get("document_id") ?? "";
  const entityTypeParam = searchParams.get("entity_type") ?? "";
  const page = Math.max(1, Number(searchParams.get("page") ?? "1") || 1);

  useEffect(() => {
    setQueryText(queryTextParam);
    setDocumentIdInput(documentIdParam);
    setEntityTypeInput(entityTypeParam);
  }, [documentIdParam, entityTypeParam, queryTextParam]);

  function updateParams(
    updates: Record<string, string | null | undefined>,
    resetPage = false
  ) {
    const next = new URLSearchParams(searchParams);
    for (const [key, value] of Object.entries(updates)) {
      if (!value) {
        next.delete(key);
      } else {
        next.set(key, value);
      }
    }
    if (resetPage) {
      next.delete("page");
    }
    setSearchParams(next);
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    updateParams(
      {
        document_id: documentIdInput.trim() || null,
        entity_type: entityTypeInput.trim() || null,
        q: queryText.trim() || null
      },
      true
    );
  }

  const scopeQuery = buildReadScopeParams();
  const searchQuery: SearchQuery = {
    q: queryTextParam || "",
    mode: modeParam,
    page,
    page_size: 10,
    document_id: documentIdParam || undefined,
    entity_type: entityTypeParam || undefined,
    file_type: fileTypeParam || undefined,
    ...scopeQuery
  };

  const resultsQuery = useQuery({
    enabled: isReady && queryTextParam.length > 0,
    queryFn: () => readSearchResults(searchQuery),
    queryKey: ["search-results", searchQuery]
  });

  return (
    <Stack gap="xl">
      <Stack gap={4}>
        <Title order={2}>Search</Title>
        <Text c="dimmed">
          Query the current Space scope across retrieval modes without leaving the workspace.
        </Text>
        <Badge color={allSpaces ? "blue" : "teal"} variant="light" w="fit-content">
          {allSpaces ? "Reading across all Spaces" : activeSpace?.name ?? "One active Space"}
        </Badge>
      </Stack>

      <Card withBorder radius="lg" p="lg">
        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            <TextInput
              label="Search query"
              placeholder="Find architecture decisions or implementation details"
              value={queryText}
              onChange={(event) => setQueryText(event.currentTarget.value)}
            />
            <SimpleGrid cols={{ base: 1, md: 2 }}>
              <Select
                data={SEARCH_MODE_OPTIONS}
                label="Retrieval mode"
                value={modeParam}
                onChange={(value) =>
                  updateParams({ mode: value ?? "combined" }, true)
                }
              />
              <Select
                clearable
                data={FILE_TYPE_OPTIONS}
                label="File type"
                placeholder="All file types"
                value={fileTypeParam || null}
                onChange={(value) => updateParams({ file_type: value }, true)}
              />
            </SimpleGrid>
            <SimpleGrid cols={{ base: 1, md: 2 }}>
              <TextInput
                label="Document ID filter"
                placeholder="Optional document UUID"
                value={documentIdInput}
                onChange={(event) => setDocumentIdInput(event.currentTarget.value)}
              />
              <TextInput
                label="Entity type filter"
                placeholder="Optional entity type"
                value={entityTypeInput}
                onChange={(event) => setEntityTypeInput(event.currentTarget.value)}
              />
            </SimpleGrid>
            <Group justify="space-between">
              <Text c="dimmed" size="sm">
                Empty query state stays idle until you run a search.
              </Text>
              <Button type="submit">Run search</Button>
            </Group>
          </Stack>
        </form>
      </Card>

      {!queryTextParam ? (
        <Alert color="blue" title="Search is ready">
          Enter a query to load retrieval results for the current scope.
        </Alert>
      ) : resultsQuery.error instanceof ApiProblemError ? (
        <Alert color="red" title="Unable to load search results">
          {resultsQuery.error.problem.detail}
        </Alert>
      ) : resultsQuery.isLoading ? (
        <Text c="dimmed">Loading search results…</Text>
      ) : resultsQuery.data && resultsQuery.data.items.length > 0 ? (
        <Stack gap="md">
          <Group justify="space-between">
            <Title order={3}>Results</Title>
            <Badge variant="light">{resultsQuery.data.total} matches</Badge>
          </Group>
          {resultsQuery.data.items.map((item) => (
            <Card key={item.result_id} withBorder radius="lg" p="lg">
              <Stack gap="md">
                <Group justify="space-between" align="start">
                  <Stack gap={2}>
                    <Title order={4}>
                      {item.document?.title ??
                        item.entity?.display_name ??
                        "Retrieval result"}
                    </Title>
                    <Text c="dimmed" size="sm">
                      {item.result_kind === "entity"
                        ? item.entity?.entity_type ?? "entity"
                        : item.document?.file_type?.toUpperCase() ?? "document"}
                    </Text>
                  </Stack>
                  <Group gap="xs">
                    <Badge variant="light">Score {formatScore(item.score)}</Badge>
                    {item.matched_modes?.map((mode) => (
                      <Badge key={mode} color="teal" variant="dot">
                        {formatSearchMode(mode)}
                      </Badge>
                    ))}
                  </Group>
                </Group>

                <Text>{item.preview_text}</Text>

                {item.citations && item.citations.length > 0 ? (
                  <Stack gap="xs">
                    <Text fw={600} size="sm">
                      Citations
                    </Text>
                    {item.citations.map((citation, index) => (
                      <Text key={`${item.result_id}-${index}`} size="sm">
                        {formatCitationLabel(citation)} · {formatSourceTier(citation.source_tier)}
                      </Text>
                    ))}
                  </Stack>
                ) : null}

                <Group>
                  {item.document?.id ? (
                    <Button
                      component={Link}
                      to={`/documents/${item.document.id}`}
                      variant="light"
                    >
                      Open document
                    </Button>
                  ) : null}
                  {item.entity?.id ? (
                    <Button
                      component={Link}
                      to={`/entities/${item.entity.id}`}
                      variant="subtle"
                    >
                      Open entity
                    </Button>
                  ) : null}
                </Group>
              </Stack>
            </Card>
          ))}
          <Group justify="center">
            <Pagination
              total={Math.max(1, Math.ceil(resultsQuery.data.total / resultsQuery.data.page_size))}
              value={page}
              onChange={(nextPage) => updateParams({ page: String(nextPage) })}
            />
          </Group>
        </Stack>
      ) : queryTextParam ? (
        <Text c="dimmed">No results match the current query and scope.</Text>
      ) : null}
    </Stack>
  );
}
