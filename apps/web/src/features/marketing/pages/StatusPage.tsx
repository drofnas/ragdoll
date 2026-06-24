import { Anchor, Alert, Badge, Card, Group, SimpleGrid, Stack, Table, Text, Title } from "@mantine/core";
import { useQuery } from "@tanstack/react-query";

import { ApiProblemError, resolveApiBaseUrl } from "../../../shared/api/client";
import { readRuntimeStatus } from "../../../shared/api/runtimeStatus";
import { formatDateTime, humanizeLabel } from "../../../shared/lib/formatting";

function StatusBadge({ value }: { value: string }) {
  const color =
    value === "healthy" || value === "ok" || value === "present"
      ? "teal"
      : value === "degraded" || value === "unknown"
        ? "yellow"
        : value === "unhealthy" || value === "missing"
          ? "red"
          : "gray";

  return (
    <Badge color={color} variant="light">
      {humanizeLabel(value)}
    </Badge>
  );
}

export function StatusPage() {
  const statusQuery = useQuery({
    queryFn: readRuntimeStatus,
    queryKey: ["public-runtime-status"],
    refetchInterval: 30000,
  });
  const backendStatusUrl = `${resolveApiBaseUrl()}/status`;
  const backendStatusJsonUrl = `${backendStatusUrl}?type=json`;

  return (
    <Stack gap="xl">
      <Stack gap={6}>
        <Group justify="space-between" align="flex-start">
          <Stack gap={4}>
            <Text tt="uppercase" c="dimmed" fw={700} size="xs">
              Public Runtime Status
            </Text>
            <Title order={1}>Workspace status</Title>
            <Text c="dimmed" maw={760}>
              Review live backend readiness, storage and model availability, and the current service posture for this self-hosted workspace.
            </Text>
          </Stack>
          <StatusBadge value={statusQuery.data?.status ?? "unknown"} />
        </Group>
        <Group gap="md">
          <Anchor href={backendStatusUrl} target="_blank" rel="noreferrer">
            Raw backend status page
          </Anchor>
          <Anchor href={backendStatusJsonUrl} target="_blank" rel="noreferrer">
            Runtime JSON
          </Anchor>
        </Group>
      </Stack>

      {statusQuery.error instanceof ApiProblemError ? (
        <Alert color="red" title="Unable to load runtime status">
          {statusQuery.error.problem.detail}
        </Alert>
      ) : null}

      <SimpleGrid cols={{ base: 1, md: 3 }}>
        <Card withBorder radius="lg" p="lg">
          <Stack gap="sm">
            <Text c="dimmed" fw={600} size="sm">
              Application
            </Text>
            <Title order={3}>{statusQuery.data?.application.name ?? "Loading…"}</Title>
            <Text>Environment: {statusQuery.data?.application.environment ?? "Loading…"}</Text>
            <Text>Version: {statusQuery.data?.application.version ?? "Loading…"}</Text>
            <Text>Generated: {formatDateTime(statusQuery.data?.application.generated_at)}</Text>
          </Stack>
        </Card>

        <Card withBorder radius="lg" p="lg">
          <Stack gap="sm">
            <Text c="dimmed" fw={600} size="sm">
              Supabase-backed services
            </Text>
            <Group justify="space-between">
              <Text>Overall</Text>
              <StatusBadge value={statusQuery.data?.supabase.status ?? "unknown"} />
            </Group>
            <Text>{statusQuery.data?.supabase.detail ?? "Checking runtime dependencies…"}</Text>
            <Text size="sm" c="dimmed">
              Backend: {statusQuery.data?.supabase.backend ?? "unknown"}
            </Text>
          </Stack>
        </Card>

        <Card withBorder radius="lg" p="lg">
          <Stack gap="sm">
            <Text c="dimmed" fw={600} size="sm">
              Ollama
            </Text>
            <Group justify="space-between">
              <Text>Overall</Text>
              <StatusBadge value={statusQuery.data?.ollama.status ?? "unknown"} />
            </Group>
            <Text>{statusQuery.data?.ollama.detail ?? "Checking model catalog…"}</Text>
            <Text size="sm" c="dimmed">
              Catalog reachable: {statusQuery.data?.ollama.catalog_reachable ? "Yes" : "No"}
            </Text>
          </Stack>
        </Card>
      </SimpleGrid>

      <Card withBorder radius="lg" p="lg">
        <Stack gap="md">
          <Group justify="space-between">
            <Title order={3}>Service overview</Title>
            {statusQuery.data ? <StatusBadge value={statusQuery.data.status} /> : null}
          </Group>
          {statusQuery.data ? (
            <Table>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Service</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th>Detail</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {Object.entries(statusQuery.data.services).map(([name, service]) => (
                  <Table.Tr key={name}>
                    <Table.Td>{humanizeLabel(name)}</Table.Td>
                    <Table.Td>
                      <StatusBadge value={service.status} />
                    </Table.Td>
                    <Table.Td>{service.detail}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          ) : (
            <Text c="dimmed">Loading service overview…</Text>
          )}
        </Stack>
      </Card>

      <Card withBorder radius="lg" p="lg">
        <Stack gap="md">
          <Title order={3}>Configured models</Title>
          {statusQuery.data?.ollama.configured_models.length ? (
            <Table>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Model</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th>Roles</Table.Th>
                  <Table.Th>Detail</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {statusQuery.data.ollama.configured_models.map((model) => (
                  <Table.Tr key={model.name}>
                    <Table.Td>{model.name}</Table.Td>
                    <Table.Td>
                      <StatusBadge value={model.status} />
                    </Table.Td>
                    <Table.Td>{model.roles.length ? model.roles.join(", ") : "none"}</Table.Td>
                    <Table.Td>{model.detail}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          ) : (
            <Text c="dimmed">No configured models were reported.</Text>
          )}
        </Stack>
      </Card>
    </Stack>
  );
}
