import { AppShell, Anchor, Container, Group, Text } from "@mantine/core";
import { Outlet, Link } from "react-router-dom";

export function PublicShell() {
  return (
    <AppShell header={{ height: 68 }} padding="md">
      <AppShell.Header>
        <Container size="lg" h="100%">
          <Group justify="space-between" h="100%">
            <Text fw={700}>Ragdoll</Text>
            <Group gap="lg">
              <Anchor component={Link} to="/login">
                Login
              </Anchor>
              <Anchor component={Link} to="/register">
                Register
              </Anchor>
              <Anchor component={Link} to="/status">
                Status
              </Anchor>
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
