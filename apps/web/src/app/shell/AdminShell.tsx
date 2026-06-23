import { AppShell, Anchor, Badge, Button, Container, Group, Stack, Text } from "@mantine/core";
import { Link, Outlet } from "react-router-dom";

import { useAuthSession } from "../../shared/state/authSession";

export function AdminShell() {
  const { logout } = useAuthSession();

  return (
    <AppShell header={{ height: 72 }} padding="md">
      <AppShell.Header>
        <Container size="lg" h="100%">
          <Group justify="space-between" h="100%">
            <Stack gap={0}>
              <Text fw={700}>Ragdoll</Text>
              <Text size="xs" c="dimmed">
                Operator admin surface
              </Text>
            </Stack>
            <Group gap="lg">
              <Anchor component={Link} to="/dashboard">
                Dashboard
              </Anchor>
              <Anchor component={Link} to="/admin">
                Admin
              </Anchor>
              <Badge color="red" variant="light">
                admin
              </Badge>
              <Button variant="light" onClick={logout}>
                Log out
              </Button>
            </Group>
          </Group>
        </Container>
      </AppShell.Header>
      <AppShell.Main>
        <Container size="lg" py="xl">
          <Outlet />
        </Container>
      </AppShell.Main>
    </AppShell>
  );
}
