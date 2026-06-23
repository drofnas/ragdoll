import { Alert, Badge, Button, Card, Group, SimpleGrid, Stack, Text, Title } from "@mantine/core";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { ApiProblemError } from "../../../shared/api/client";
import { formatDateTime } from "../../../shared/lib/formatting";
import { useSpaceScope } from "../../../shared/state/spaceScope";
import { readUsageSummary } from "../../account/api/accountApi";
import { listDocuments } from "../../documents/api/documentsApi";

export function DashboardPage() {
  const { activeSpace, allSpaces, buildReadScopeParams, isReady } = useSpaceScope();
  const scopeQuery = buildReadScopeParams();

  const documentsQuery = useQuery({
    enabled: isReady,
    queryFn: () =>
      listDocuments({
        page: 1,
        page_size: 5,
        ...scopeQuery
      }),
    queryKey: ["dashboard-documents", scopeQuery]
  });

  const usageQuery = useQuery({
    queryFn: readUsageSummary,
    queryKey: ["dashboard-usage"]
  });

  return (
    <Stack gap="xl">
      <Stack gap={4}>
        <Title order={2}>Workspace dashboard</Title>
        <Group gap="sm">
          <Badge color={allSpaces ? "blue" : "teal"} variant="light">
            {allSpaces ? "All spaces" : activeSpace?.name ?? "No active space"}
          </Badge>
          <Text c="dimmed">Use the shell scope controls to change what this dashboard summarizes.</Text>
        </Group>
      </Stack>

      <SimpleGrid cols={{ base: 1, md: 3 }}>
        <Card withBorder radius="lg" p="lg">
          <Stack gap={4}>
            <Text fw={600}>Documents in scope</Text>
            <Text size="xl">{documentsQuery.data?.total ?? 0}</Text>
          </Stack>
        </Card>
        <Card withBorder radius="lg" p="lg">
          <Stack gap={4}>
            <Text fw={600}>Configured retrieval budget</Text>
            <Text size="xl">{usageQuery.data?.limits.retrieval_chunks ?? "loading"}</Text>
            <Text c="dimmed" size="sm">
              Chunks available to retrieval-backed features
            </Text>
          </Stack>
        </Card>
        <Card withBorder radius="lg" p="lg">
          <Stack gap={4}>
            <Text fw={600}>Upload status</Text>
            <Text size="xl">{usageQuery.data?.status.partially_indexed_documents ?? 0}</Text>
            <Text c="dimmed" size="sm">
              Documents still working through processing
            </Text>
          </Stack>
        </Card>
      </SimpleGrid>

      {documentsQuery.error instanceof ApiProblemError ? (
        <Alert color="red" title="Unable to load recent documents">
          {documentsQuery.error.problem.detail}
        </Alert>
      ) : null}

      <Card withBorder radius="lg" p="lg">
        <Stack gap="md">
          <Group justify="space-between">
            <Title order={4}>Recent documents</Title>
            <Button component={Link} to="/documents" variant="subtle">
              Open library
            </Button>
          </Group>
          {documentsQuery.isLoading ? (
            <Text c="dimmed">Loading recent documents…</Text>
          ) : documentsQuery.data && documentsQuery.data.items.length > 0 ? (
            <Stack gap="sm">
              {documentsQuery.data.items.map((document) => (
                <Group key={document.id} justify="space-between" wrap="nowrap">
                  <Stack gap={0}>
                    <Text fw={600}>{document.title}</Text>
                    <Text c="dimmed" size="sm">
                      {document.original_filename}
                    </Text>
                  </Stack>
                  <Stack align="end" gap={0}>
                    <Text size="sm">{document.processing_status.overall}</Text>
                    <Text c="dimmed" size="xs">
                      {formatDateTime(document.updated_at)}
                    </Text>
                  </Stack>
                </Group>
              ))}
            </Stack>
          ) : (
            <Text c="dimmed">Upload a document to start filling in the dashboard.</Text>
          )}
        </Stack>
      </Card>
    </Stack>
  );
}
