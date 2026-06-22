import { Alert, Badge, Button, Card, Group, Select, SimpleGrid, Stack, Text, Title } from "@mantine/core";
import { useQuery } from "@tanstack/react-query";
import { Link, Navigate, useParams, useSearchParams } from "react-router-dom";

import { ApiProblemError } from "../../../shared/api/client";
import {
  formatCitationLabel,
  formatDateTime,
  formatSourceTier
} from "../../../shared/lib/formatting";
import { useSpaceScope } from "../../../shared/state/spaceScope";
import { readEntity, readEntitySubgraph } from "../api/entitiesApi";

const DEPTH_OPTIONS = [
  { label: "1 hop", value: "1" },
  { label: "2 hops", value: "2" },
  { label: "3 hops", value: "3" }
];

const LIMIT_OPTIONS = [
  { label: "10 links", value: "10" },
  { label: "25 links", value: "25" },
  { label: "50 links", value: "50" }
];

export function EntityDetailPage() {
  const { entityId } = useParams<{ entityId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const { buildReadScopeParams } = useSpaceScope();

  const depth = Math.max(1, Number(searchParams.get("depth") ?? "1") || 1);
  const limit = Math.max(1, Number(searchParams.get("limit") ?? "25") || 25);
  const scopeQuery = buildReadScopeParams();

  if (!entityId) {
    return <Navigate to="/entities" replace />;
  }

  const detailQuery = useQuery({
    queryFn: () => readEntity(entityId, scopeQuery),
    queryKey: ["entity-detail", entityId, scopeQuery]
  });

  const graphQuery = useQuery({
    queryFn: () =>
      readEntitySubgraph(entityId, {
        depth,
        limit,
        ...scopeQuery
      }),
    queryKey: ["entity-graph", entityId, depth, limit, scopeQuery]
  });

  function updateGraphParams(next: Record<string, string>) {
    const params = new URLSearchParams(searchParams);
    for (const [key, value] of Object.entries(next)) {
      params.set(key, value);
    }
    setSearchParams(params);
  }

  return (
    <Stack gap="xl">
      <Group justify="space-between" align="end">
        <Stack gap={4}>
          <Button component={Link} to="/entities" variant="subtle">
            Back to entities
          </Button>
          <Title order={2}>{detailQuery.data?.display_name ?? "Entity detail"}</Title>
          <Text c="dimmed">{detailQuery.data?.entity_type ?? "Loading entity metadata"}</Text>
        </Stack>
        {detailQuery.data ? (
          <Badge variant="light">{detailQuery.data.document_count} documents</Badge>
        ) : null}
      </Group>

      {detailQuery.error instanceof ApiProblemError ? (
        <Alert color="red" title="Unable to load the selected entity">
          {detailQuery.error.problem.detail}
        </Alert>
      ) : detailQuery.isLoading ? (
        <Text c="dimmed">Loading entity detail…</Text>
      ) : detailQuery.data ? (
        <>
          <SimpleGrid cols={{ base: 1, lg: 3 }}>
            <Card withBorder radius="lg" p="lg">
              <Stack gap="xs">
                <Title order={4}>Overview</Title>
                <Text>Normalized name: {detailQuery.data.normalized_name}</Text>
                <Text>Mentions: {detailQuery.data.mention_count}</Text>
                <Text>Latest mention: {formatDateTime(detailQuery.data.latest_mentioned_at)}</Text>
              </Stack>
            </Card>
            <Card withBorder radius="lg" p="lg">
              <Stack gap="xs">
                <Title order={4}>Graph controls</Title>
                <Select
                  data={DEPTH_OPTIONS}
                  label="Depth"
                  value={String(depth)}
                  onChange={(value) => updateGraphParams({ depth: value ?? "1" })}
                />
                <Select
                  data={LIMIT_OPTIONS}
                  label="Limit"
                  value={String(limit)}
                  onChange={(value) => updateGraphParams({ limit: value ?? "25" })}
                />
              </Stack>
            </Card>
            <Card withBorder radius="lg" p="lg">
              <Stack gap="xs">
                <Title order={4}>Related docs</Title>
                <Text>{detailQuery.data.related_documents?.length ?? 0} linked documents</Text>
                <Text>{graphQuery.data?.links?.length ?? 0} graph links loaded</Text>
              </Stack>
            </Card>
          </SimpleGrid>

          <SimpleGrid cols={{ base: 1, lg: 2 }}>
            <Card withBorder radius="lg" p="lg">
              <Stack gap="md">
                <Title order={4}>Provenance</Title>
                {detailQuery.data.provenance && detailQuery.data.provenance.length > 0 ? (
                  detailQuery.data.provenance.map((mention) => (
                    <Card key={mention.mention_id} withBorder radius="md" p="sm">
                      <Stack gap={4}>
                        <Text fw={600}>{mention.surface_text}</Text>
                        <Text size="sm">
                          {formatCitationLabel(mention.citation)} · {formatSourceTier(mention.citation.source_tier)}
                        </Text>
                        <Text c="dimmed" size="sm">
                          Mentioned {formatDateTime(mention.created_at)}
                        </Text>
                      </Stack>
                    </Card>
                  ))
                ) : (
                  <Text c="dimmed">No provenance records are available yet.</Text>
                )}
              </Stack>
            </Card>

            <Card withBorder radius="lg" p="lg">
              <Stack gap="md">
                <Title order={4}>Mention history</Title>
                {detailQuery.data.history && detailQuery.data.history.length > 0 ? (
                  detailQuery.data.history.map((entry) => (
                    <Card key={entry.mention_id} withBorder radius="md" p="sm">
                      <Stack gap={4}>
                        <Text fw={600}>{entry.surface_text}</Text>
                        <Text size="sm">
                          {formatCitationLabel(entry.citation)} · observed {formatDateTime(entry.observed_at)}
                        </Text>
                      </Stack>
                    </Card>
                  ))
                ) : (
                  <Text c="dimmed">No chronological mention history is available yet.</Text>
                )}
              </Stack>
            </Card>
          </SimpleGrid>

          <SimpleGrid cols={{ base: 1, lg: 2 }}>
            <Card withBorder radius="lg" p="lg">
              <Stack gap="md">
                <Title order={4}>Related documents</Title>
                {detailQuery.data.related_documents &&
                detailQuery.data.related_documents.length > 0 ? (
                  detailQuery.data.related_documents.map((document) => (
                    <Group key={document.document_id} justify="space-between" align="start">
                      <Stack gap={2}>
                        <Button
                          component={Link}
                          size="compact-sm"
                          to={`/documents/${document.document_id}`}
                          variant="subtle"
                        >
                          {document.title}
                        </Button>
                        <Text c="dimmed" size="sm">
                          {document.file_type.toUpperCase()} · {document.mention_count} mentions
                        </Text>
                      </Stack>
                      <Text c="dimmed" size="sm">
                        {formatDateTime(document.latest_mentioned_at)}
                      </Text>
                    </Group>
                  ))
                ) : (
                  <Text c="dimmed">No related documents are linked yet.</Text>
                )}
              </Stack>
            </Card>

            <Card withBorder radius="lg" p="lg">
              <Stack gap="md">
                <Title order={4}>Lightweight graph view</Title>
                {graphQuery.error instanceof ApiProblemError ? (
                  <Alert color="red" title="Unable to load graph links">
                    {graphQuery.error.problem.detail}
                  </Alert>
                ) : graphQuery.isLoading ? (
                  <Text c="dimmed">Loading graph relationships…</Text>
                ) : graphQuery.data ? (
                  <>
                    <Stack gap="xs">
                      <Text fw={600} size="sm">
                        Nodes
                      </Text>
                      {graphQuery.data.nodes && graphQuery.data.nodes.length > 0 ? (
                        graphQuery.data.nodes.map((node) => (
                          <Text key={node.id} size="sm">
                            {node.label} · {node.node_type}
                          </Text>
                        ))
                      ) : (
                        <Text c="dimmed" size="sm">
                          No nodes were returned for this depth and limit.
                        </Text>
                      )}
                    </Stack>
                    <Stack gap="xs">
                      <Text fw={600} size="sm">
                        Links
                      </Text>
                      {graphQuery.data.links && graphQuery.data.links.length > 0 ? (
                        graphQuery.data.links.map((link, index) => (
                          <Text key={`${link.source_id}-${link.target_id}-${index}`} size="sm">
                            {link.source_id} → {link.target_id} · {link.relation_type}
                          </Text>
                        ))
                      ) : (
                        <Text c="dimmed" size="sm">
                          No relationship links were returned for this entity.
                        </Text>
                      )}
                    </Stack>
                  </>
                ) : null}
              </Stack>
            </Card>
          </SimpleGrid>
        </>
      ) : null}
    </Stack>
  );
}
