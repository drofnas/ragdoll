import { useEffect, useState, type FormEvent } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  Divider,
  Group,
  List,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Title
} from "@mantine/core";
import { useQuery } from "@tanstack/react-query";

import { ApiProblemError } from "../../../shared/api/client";
import { formatDateTime } from "../../../shared/lib/formatting";
import { useAuthSession } from "../../../shared/state/authSession";
import { updateCurrentUser } from "../../auth/api/authApi";
import { readUsageSummary } from "../api/accountApi";

export function AccountPage() {
  const { currentUser, refreshSession } = useAuthSession();
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const usageQuery = useQuery({
    queryFn: readUsageSummary,
    queryKey: ["usage-summary"]
  });

  useEffect(() => {
    setEmail(currentUser?.email ?? "");
    setFullName(currentUser?.full_name ?? "");
  }, [currentUser]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage(null);
    setSuccessMessage(null);
    setIsSaving(true);

    try {
      await updateCurrentUser({
        current_password: currentPassword || null,
        email,
        full_name: fullName || null,
        new_password: newPassword || null
      });
      await refreshSession();
      setCurrentPassword("");
      setNewPassword("");
      setSuccessMessage("Profile updated.");
    } catch (error) {
      if (error instanceof ApiProblemError) {
        setErrorMessage(error.problem.detail);
      } else {
        setErrorMessage("Unable to save your account changes right now.");
      }
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <Stack gap="xl">
      <Stack gap={4}>
        <Title order={2}>Account</Title>
        <Text c="dimmed">Manage your profile, password, and current usage envelope.</Text>
      </Stack>

      {errorMessage ? (
        <Alert color="red" title="Account update failed">
          {errorMessage}
        </Alert>
      ) : null}

      {successMessage ? (
        <Alert color="teal" title="Saved">
          {successMessage}
        </Alert>
      ) : null}

      <SimpleGrid cols={{ base: 1, lg: 2 }}>
        <Card withBorder radius="lg" p="lg">
          <Stack gap="md">
            <Title order={4}>Profile</Title>
            <form onSubmit={handleSubmit}>
              <Stack gap="md">
                <TextInput
                  autoComplete="name"
                  label="Full name"
                  value={fullName}
                  onChange={(event) => setFullName(event.currentTarget.value)}
                />
                <TextInput
                  autoComplete="email"
                  label="Email"
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.currentTarget.value)}
                />
                <TextInput
                  autoComplete="current-password"
                  label="Current password"
                  placeholder="Required only when changing your password"
                  type="password"
                  value={currentPassword}
                  onChange={(event) => setCurrentPassword(event.currentTarget.value)}
                />
                <TextInput
                  autoComplete="new-password"
                  label="New password"
                  placeholder="Leave blank to keep the current password"
                  type="password"
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.currentTarget.value)}
                />
                <Button loading={isSaving} type="submit">
                  Save account changes
                </Button>
              </Stack>
            </form>
          </Stack>
        </Card>

        <Card withBorder radius="lg" p="lg">
          <Stack gap="md">
            <Group justify="space-between">
              <Title order={4}>Profile state</Title>
              <Badge variant="light">{currentUser?.is_active ? "Active" : "Disabled"}</Badge>
            </Group>
            <Text>Last login: {formatDateTime(currentUser?.last_login)}</Text>
            <Text>Admin access: {currentUser?.is_admin ? "Yes" : "No"}</Text>
            <Text>Password rotation required: {currentUser?.must_change_password ? "Yes" : "No"}</Text>
            <Divider />
            <Title order={5}>Instance policy</Title>
            <List size="sm">
              <List.Item>Usage limits are controlled by self-hosted instance configuration.</List.Item>
              <List.Item>Administrators can manage access, password rotation, and operator workflows.</List.Item>
            </List>
          </Stack>
        </Card>
      </SimpleGrid>

      <Card withBorder radius="lg" p="lg">
        <Stack gap="md">
          <Group justify="space-between">
            <Title order={4}>Usage summary</Title>
            <Badge variant="light">Config-driven</Badge>
          </Group>

          {usageQuery.isLoading ? (
            <Text c="dimmed">Loading usage…</Text>
          ) : usageQuery.error instanceof ApiProblemError ? (
            <Alert color="red" title="Unable to load usage">
              {usageQuery.error.problem.detail}
            </Alert>
          ) : usageQuery.data ? (
            <SimpleGrid cols={{ base: 1, md: 3 }}>
              <Card withBorder radius="md" p="md">
                <Stack gap={2}>
                  <Text fw={600}>Documents</Text>
                  <Text>{usageQuery.data.usage.documents}</Text>
                  <Text c="dimmed" size="sm">
                    Limit: {usageQuery.data.limits.documents ?? "unlimited"}
                  </Text>
                </Stack>
              </Card>
              <Card withBorder radius="md" p="md">
                <Stack gap={2}>
                  <Text fw={600}>Chunks</Text>
                  <Text>{usageQuery.data.usage.chunks}</Text>
                  <Text c="dimmed" size="sm">
                    Limit: {usageQuery.data.limits.chunks ?? "unlimited"}
                  </Text>
                </Stack>
              </Card>
              <Card withBorder radius="md" p="md">
                <Stack gap={2}>
                  <Text fw={600}>Storage</Text>
                  <Text>{usageQuery.data.usage.storage_bytes} bytes</Text>
                  <Text c="dimmed" size="sm">
                    Limit: {usageQuery.data.limits.storage_bytes ?? "unlimited"}
                  </Text>
                </Stack>
              </Card>
            </SimpleGrid>
          ) : null}
        </Stack>
      </Card>
    </Stack>
  );
}
