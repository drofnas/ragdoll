import { useEffect, useState, type FormEvent } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  Group,
  Pagination,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Title
} from "@mantine/core";
import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";

import { ApiProblemError } from "../../../shared/api/client";
import { formatDateTime } from "../../../shared/lib/formatting";
import { useSpaceScope } from "../../../shared/state/spaceScope";
import { listEntities, type ListEntitiesQuery } from "../api/entitiesApi";

export function EntitiesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { activeSpace, allSpaces, buildReadScopeParams, isReady } = useSpaceScope();
  const [queryText, setQueryText] = useState(searchParams.get("q") ?? "");
  const [entityTypeText, setEntityTypeText] = useState(searchParams.get("entity_type") ?? "");

  const queryTextParam = searchParams.get("q") ?? "";
  const entityTypeParam = searchParams.get("entity_type") ?? "";
  const page = Math.max(1, Number(searchParams.get("page") ?? "1") || 1);

  useEffect(() => {
    setQueryText(queryTextParam);
    setEntityTypeText(entityTypeParam);
  }, [entityTypeParam, queryTextParam]);

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
        entity_type: entityTypeText.trim() || null,
        q: queryText.trim() || null
      },
      true
    );
  }

  const scopeQuery = buildReadScopeParams();
  const entityQuery: ListEntitiesQuery = {
    page,
    page_size: 12,
    q: queryTextParam || undefined,
    entity_type: entityTypeParam || undefined,
    ...scopeQuery
  };

  const entitiesQuery = useQuery({
    enabled: isReady,
    queryFn: () => listEntities(entityQuery),
    queryKey: ["entities", entityQuery]
  });

  return (
    <Stack gap="xl">
      <Stack gap={4}>
        <Title order={2}>Entities</Title>
        <Text c="dimmed">
          Explore extracted entities, their provenance, and how often they appear in the current scope.
        </Text>
        <Badge color={allSpaces ? "blue" : "teal"} variant="light" w="fit-content">
          {allSpaces ? "Reading across all Spaces" : activeSpace?.name ?? "One active Space"}
        </Badge>
      </Stack>

      <Card withBorder radius="lg" p="lg">
        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            <TextInput
              label="Search entities"
              placeholder="Find a person, system, or concept"
              value={queryText}
              onChange={(event) => setQueryText(event.currentTarget.value)}
            />
            <TextInput
              label="Entity type"
              placeholder="Optional entity type"
              value={entityTypeText}
              onChange={(event) => setEntityTypeText(event.currentTarget.value)}
            />
            <Group justify="flex-end">
              <Button type="submit">Apply filters</Button>
            </Group>
          </Stack>
        </form>
      </Card>

      {entitiesQuery.error instanceof ApiProblemError ? (
        <Alert color="red" title="Unable to load entities">
          {entitiesQuery.error.problem.detail}
        </Alert>
      ) : entitiesQuery.isLoading ? (
        <Text c="dimmed">Loading entities…</Text>
      ) : entitiesQuery.data && entitiesQuery.data.items.length > 0 ? (
        <Stack gap="md">
          <Group justify="space-between">
            <Title order={3}>Results</Title>
            <Badge variant="light">{entitiesQuery.data.total} entities</Badge>
          </Group>
          <SimpleGrid cols={{ base: 1, md: 2 }}>
            {entitiesQuery.data.items.map((entity) => (
              <Card key={entity.id} withBorder radius="lg" p="lg">
                <Stack gap="md">
                  <Group justify="space-between" align="start">
                    <Stack gap={2}>
                      <Title order={4}>{entity.display_name}</Title>
                      <Text c="dimmed" size="sm">
                        {entity.entity_type}
                      </Text>
                    </Stack>
                    <Badge variant="light">{entity.document_count} documents</Badge>
                  </Group>

                  <Text size="sm">
                    {entity.mention_count} mentions · latest mention {formatDateTime(entity.latest_mentioned_at)}
                  </Text>

                  <Button component={Link} to={`/entities/${entity.id}`} variant="light">
                    Open entity detail
                  </Button>
                </Stack>
              </Card>
            ))}
          </SimpleGrid>
          <Group justify="center">
            <Pagination
              total={Math.max(1, Math.ceil(entitiesQuery.data.total / entitiesQuery.data.page_size))}
              value={page}
              onChange={(nextPage) => updateParams({ page: String(nextPage) })}
            />
          </Group>
        </Stack>
      ) : (
        <Text c="dimmed">No entities match the current scope and filters.</Text>
      )}
    </Stack>
  );
}
