import { Button, Card, Group, Stack, Text, Title } from "@mantine/core";
import { Link } from "react-router-dom";

export function HomePage() {
  return (
    <Card shadow="sm" padding="xl">
      <Stack gap="md">
        <Title order={1}>Ragdoll Workspace</Title>
        <Text c="dimmed">
          The clean-room rebuild now has a live web workspace for auth, Spaces, document upload,
          processing, and account usage on top of the typed API contracts.
        </Text>
        <Group>
          <Button component={Link} to="/login">
            Sign in
          </Button>
          <Button variant="light" component={Link} to="/register">
            Create account
          </Button>
        </Group>
      </Stack>
    </Card>
  );
}
