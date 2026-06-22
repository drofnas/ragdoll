import { Card, Stack, Text, Title } from "@mantine/core";

export function AdminHomePage() {
  return (
    <Card shadow="sm" padding="xl">
      <Stack gap="sm">
        <Title order={2}>Admin Placeholder</Title>
        <Text c="dimmed">
          Admin tooling stays intentionally deferred. This route is here so auth and role gating can be validated before the later admin phase lands.
        </Text>
      </Stack>
    </Card>
  );
}
