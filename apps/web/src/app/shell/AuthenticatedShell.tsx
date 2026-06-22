import { AppShell, Anchor, Badge, Button, Container, Group, Select, Stack, Switch, Text } from "@mantine/core";
import { Link, Outlet } from "react-router-dom";

import { useAuthSession } from "../../shared/state/authSession";
import { useSpaceScope } from "../../shared/state/spaceScope";

export function AuthenticatedShell() {
  const { currentUser, isAdmin, logout } = useAuthSession();
  const { activeSpace, allSpaces, isReady, setActiveSpace, setAllSpaces, spaces } = useSpaceScope();

  return (
    <AppShell header={{ height: 96 }} padding="md">
      <AppShell.Header>
        <Container size="xl" h="100%">
          <Group justify="space-between" h="100%" wrap="nowrap">
            <Stack gap={0}>
              <Text fw={700}>Ragdoll</Text>
              <Text size="xs" c="dimmed">
                Web workspace foundations
              </Text>
            </Stack>

            <Group gap="md" wrap="nowrap">
              <Anchor component={Link} to="/dashboard">
                Dashboard
              </Anchor>
              <Anchor component={Link} to="/spaces">
                Spaces
              </Anchor>
              <Anchor component={Link} to="/documents">
                Documents
              </Anchor>
              <Anchor component={Link} to="/account">
                Account
              </Anchor>
              {isAdmin ? (
                <Anchor component={Link} to="/admin">
                  Admin
                </Anchor>
              ) : null}
            </Group>

            <Group gap="sm" wrap="nowrap">
              <Select
                data={spaces.map((space) => ({ label: space.name, value: space.id }))}
                disabled={!isReady || allSpaces}
                placeholder="Choose a Space"
                value={activeSpace?.id ?? null}
                onChange={(value) => setActiveSpace(spaces.find((space) => space.id === value) ?? null)}
              />
              <Switch checked={allSpaces} label="All spaces" onChange={(event) => setAllSpaces(event.currentTarget.checked)} />
              <Badge color={allSpaces ? "blue" : "teal"} variant="light">
                {allSpaces ? "reading across all Spaces" : activeSpace?.name ?? "single Space"}
              </Badge>
              <Stack gap={0} align="end">
                <Text size="sm" fw={600}>
                  {currentUser?.full_name ?? currentUser?.email}
                </Text>
                <Text size="xs" c="dimmed">
                  {currentUser?.email}
                </Text>
              </Stack>
              <Button variant="light" onClick={logout}>
                Log out
              </Button>
            </Group>
          </Group>
        </Container>
      </AppShell.Header>
      <AppShell.Main>
        <Container size="xl" py="xl">
          <Outlet />
        </Container>
      </AppShell.Main>
    </AppShell>
  );
}
