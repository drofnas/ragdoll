import { Card, Stack, Text, Title } from "@mantine/core";

export function RegisterPage() {
  return (
    <Card shadow="sm" padding="xl">
      <Stack gap="sm">
        <Title order={2}>Register Placeholder</Title>
        <Text c="dimmed">
          Registration flows will be wired once auth contracts and backend module routes land.
        </Text>
      </Stack>
    </Card>
  );
}
