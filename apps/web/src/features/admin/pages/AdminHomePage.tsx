import { Card, Stack, Text, Title } from "@mantine/core";

export function AdminHomePage() {
  return (
    <Card shadow="sm" padding="xl">
      <Stack gap="sm">
        <Title order={2}>Admin Placeholder</Title>
        <Text c="dimmed">
          Admin feature pages and runtime testers will be added after shared contracts and core backend modules exist.
        </Text>
      </Stack>
    </Card>
  );
}
