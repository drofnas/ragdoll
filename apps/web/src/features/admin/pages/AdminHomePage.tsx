import {
  Alert,
  Badge,
  Button,
  Card,
  Group,
  SimpleGrid,
  Stack,
  Switch,
  Table,
  Text,
  Title,
} from "@mantine/core";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { ApiProblemError } from "../../../shared/api/client";
import { formatDateTime } from "../../../shared/lib/formatting";
import {
  readAdminUser,
  readAdminUsers,
  readEffectiveLimits,
  readRuntimeStatus,
  updateAdminUser,
} from "../api/adminApi";

export function AdminHomePage() {
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  const usersQuery = useQuery({
    queryFn: () => readAdminUsers(),
    queryKey: ["admin-users"],
  });
  const limitsQuery = useQuery({
    queryFn: readEffectiveLimits,
    queryKey: ["admin-effective-limits"],
  });
  const statusQuery = useQuery({
    queryFn: readRuntimeStatus,
    queryKey: ["admin-runtime-status"],
  });
  const userDetailQuery = useQuery({
    enabled: Boolean(selectedUserId),
    queryFn: () => readAdminUser(selectedUserId!),
    queryKey: ["admin-user", selectedUserId],
  });

  async function toggleUserField(
    field: "is_active" | "is_admin" | "must_change_password",
    value: boolean
  ) {
    if (!selectedUserId) {
      return;
    }
    await updateAdminUser(selectedUserId, { [field]: value });
    await Promise.all([usersQuery.refetch(), userDetailQuery.refetch()]);
    setFeedback("User settings updated.");
  }

  return (
    <Stack gap="xl">
      <Stack gap={4}>
        <Title order={2}>Operator admin</Title>
        <Text c="dimmed">
          Review runtime readiness, inspect effective instance limits, and manage user access for this self-hosted installation.
        </Text>
      </Stack>

      {feedback ? (
        <Alert color="teal" title="Saved">
          {feedback}
        </Alert>
      ) : null}

      <SimpleGrid cols={{ base: 1, xl: 3 }}>
        <Card withBorder radius="lg" p="lg">
          <Stack gap="md">
            <Group justify="space-between">
              <Title order={4}>Runtime status</Title>
              <Badge variant="light">{statusQuery.data?.status ?? "loading"}</Badge>
            </Group>
            {statusQuery.error instanceof ApiProblemError ? (
              <Alert color="red" title="Unable to load runtime status">
                {statusQuery.error.problem.detail}
              </Alert>
            ) : statusQuery.data ? (
              <Stack gap="xs">
                {Object.entries(statusQuery.data.services).map(([name, service]) => (
                  <Group key={name} justify="space-between">
                    <Text tt="capitalize">{name}</Text>
                    <Badge variant="light">{service.status}</Badge>
                  </Group>
                ))}
              </Stack>
            ) : (
              <Text c="dimmed">Loading runtime status…</Text>
            )}
          </Stack>
        </Card>

        <Card withBorder radius="lg" p="lg">
          <Stack gap="md">
            <Title order={4}>Effective instance limits</Title>
            {limitsQuery.error instanceof ApiProblemError ? (
              <Alert color="red" title="Unable to load limits">
                {limitsQuery.error.problem.detail}
              </Alert>
            ) : limitsQuery.data ? (
              <Stack gap="xs">
                <Text>Documents: {limitsQuery.data.documents ?? "unlimited"}</Text>
                <Text>Storage: {limitsQuery.data.storage_bytes ?? "unlimited"}</Text>
                <Text>Tokens / 5h: {limitsQuery.data.tokens_5h ?? "unlimited"}</Text>
                <Text>Tokens / week: {limitsQuery.data.tokens_week ?? "unlimited"}</Text>
                <Text>Max file size: {limitsQuery.data.max_file_size_bytes ?? "unlimited"} bytes</Text>
                <Text>Per-document chunks: {limitsQuery.data.per_document_chunks}</Text>
                <Text>Retrieval chunks: {limitsQuery.data.retrieval_chunks}</Text>
                <Text>Output tokens: {limitsQuery.data.output_tokens}</Text>
                <Text>
                  Upload rate limit:{" "}
                  {limitsQuery.data.upload_rate_limit.enabled
                    ? `${limitsQuery.data.upload_rate_limit.requests} per ${limitsQuery.data.upload_rate_limit.window_seconds}s`
                    : "disabled"}
                </Text>
              </Stack>
            ) : (
              <Text c="dimmed">Loading limits…</Text>
            )}
          </Stack>
        </Card>

        <Card withBorder radius="lg" p="lg">
          <Stack gap="md">
            <Title order={4}>Selected user</Title>
            {userDetailQuery.error instanceof ApiProblemError ? (
              <Alert color="red" title="Unable to load user">
                {userDetailQuery.error.problem.detail}
              </Alert>
            ) : userDetailQuery.data ? (
              <Stack gap="sm">
                <Text fw={600}>{userDetailQuery.data.full_name ?? userDetailQuery.data.email}</Text>
                <Text c="dimmed" size="sm">
                  {userDetailQuery.data.email}
                </Text>
                <Text>Last login: {formatDateTime(userDetailQuery.data.last_login)}</Text>
                <Switch
                  checked={userDetailQuery.data.is_active}
                  label="Active account"
                  onChange={(event) => void toggleUserField("is_active", event.currentTarget.checked)}
                />
                <Switch
                  checked={userDetailQuery.data.is_admin}
                  label="Admin access"
                  onChange={(event) => void toggleUserField("is_admin", event.currentTarget.checked)}
                />
                <Switch
                  checked={userDetailQuery.data.must_change_password}
                  label="Require password change"
                  onChange={(event) =>
                    void toggleUserField("must_change_password", event.currentTarget.checked)
                  }
                />
              </Stack>
            ) : (
              <Text c="dimmed">Choose a user from the table to inspect and manage account state.</Text>
            )}
          </Stack>
        </Card>
      </SimpleGrid>

      <Card withBorder radius="lg" p="lg">
        <Stack gap="md">
          <Title order={4}>User management</Title>
          {usersQuery.error instanceof ApiProblemError ? (
            <Alert color="red" title="Unable to load users">
              {usersQuery.error.problem.detail}
            </Alert>
          ) : usersQuery.data ? (
            <Table highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>User</Table.Th>
                  <Table.Th>Admin</Table.Th>
                  <Table.Th>Active</Table.Th>
                  <Table.Th>Last login</Table.Th>
                  <Table.Th />
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {usersQuery.data.items.map((user) => (
                  <Table.Tr key={user.id}>
                    <Table.Td>
                      <Stack gap={0}>
                        <Text fw={600}>{user.full_name ?? user.email}</Text>
                        <Text c="dimmed" size="sm">
                          {user.email}
                        </Text>
                      </Stack>
                    </Table.Td>
                    <Table.Td>{user.is_admin ? "Yes" : "No"}</Table.Td>
                    <Table.Td>{user.is_active ? "Yes" : "No"}</Table.Td>
                    <Table.Td>{formatDateTime(user.last_login)}</Table.Td>
                    <Table.Td>
                      <Button size="xs" variant="light" onClick={() => setSelectedUserId(user.id)}>
                        Inspect
                      </Button>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          ) : (
            <Text c="dimmed">Loading users…</Text>
          )}
        </Stack>
      </Card>
    </Stack>
  );
}
