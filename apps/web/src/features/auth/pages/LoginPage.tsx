import { Card, Stack, Text, Title } from "@mantine/core";

export function LoginPage() {
  return (
    <Card shadow="sm" padding="xl">
      <Stack gap="sm">
        <Title order={2}>Login Placeholder</Title>
        <Text c="dimmed">
          Real auth bootstrap is deferred. Use `VITE_SCAFFOLD_AUTH_MODE=user` or `admin` to preview protected shells.
        </Text>
      </Stack>
    </Card>
  );
}
