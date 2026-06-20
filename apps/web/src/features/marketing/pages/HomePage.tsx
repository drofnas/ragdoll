import { Button, Card, Group, Stack, Text, Title } from "@mantine/core";
import { Link } from "react-router-dom";

export function HomePage() {
  return (
    <Card shadow="sm" padding="xl">
      <Stack gap="md">
        <Title order={1}>Ragdoll Clean-Room Rebuild</Title>
        <Text c="dimmed">
          This Phase 1 scaffold is a shell-only frontend runtime designed to prove routing,
          providers, and role-aware layouts before feature pages are migrated.
        </Text>
        <Group>
          <Button component={Link} to="/login">
            Login Placeholder
          </Button>
          <Button variant="light" component={Link} to="/register">
            Register Placeholder
          </Button>
        </Group>
      </Stack>
    </Card>
  );
}
