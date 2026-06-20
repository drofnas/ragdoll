import { AppShell, Anchor, Badge, Container, Group, Stack, Text } from "@mantine/core";
import { Link, Outlet } from "react-router-dom";

export function AdminShell() {
  return (
    <AppShell header={{ height: 72 }} padding="md">
      <AppShell.Header>
        <Container size="lg" h="100%">
          <Group justify="space-between" h="100%">
            <Stack gap={0}>
              <Text fw={700}>Ragdoll</Text>
              <Text size="xs" c="dimmed">
                Admin scaffold
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
