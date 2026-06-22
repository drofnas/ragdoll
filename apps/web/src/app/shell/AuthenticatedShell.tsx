import {
  AppShell,
  Badge,
  Box,
  Burger,
  Button,
  Container,
  Group,
  NavLink,
  Select,
  Stack,
  Switch,
  Text
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { Link, Outlet, useLocation } from "react-router-dom";

import { useAuthSession } from "../../shared/state/authSession";
import { useSpaceScope } from "../../shared/state/spaceScope";

const primaryLinks = [
  { label: "Dashboard", to: "/dashboard" },
  { label: "Spaces", to: "/spaces" },
  { label: "Documents", to: "/documents" },
  { label: "Search", to: "/search" },
  { label: "Chat", to: "/chat" },
  { label: "Entities", to: "/entities" },
  { label: "Tracked state", to: "/tracked-state" },
  { label: "Changes", to: "/changes" },
  { label: "Account", to: "/account" }
] as const;

function isActivePath(currentPath: string, targetPath: string) {
  return currentPath === targetPath || currentPath.startsWith(`${targetPath}/`);
}

export function AuthenticatedShell() {
  const { currentUser, isAdmin, logout } = useAuthSession();
  const { activeSpace, allSpaces, isReady, setActiveSpace, setAllSpaces, spaces } = useSpaceScope();
  const [opened, { toggle, close }] = useDisclosure();
  const { pathname } = useLocation();

  return (
    <AppShell
      header={{ height: 96 }}
      navbar={{ breakpoint: "md", collapsed: { mobile: !opened }, width: 220 }}
      padding="md"
    >
      <AppShell.Header>
        <Container size="xl" h="100%">
          <Box
            h="100%"
            style={{
              alignItems: "center",
              display: "grid",
              gap: "1rem",
              gridTemplateColumns: "minmax(0, 1fr) auto minmax(0, 1fr)"
            }}
          >
            <Group gap="sm" wrap="nowrap">
              <Burger hiddenFrom="md" opened={opened} onClick={toggle} size="sm" />
              <Stack gap={0}>
                <Text fw={700}>Ragdoll</Text>
                <Text size="xs" c="dimmed">
                  Web workspace foundations
                </Text>
              </Stack>
            </Group>

            <Group gap="xs" justify="center" wrap="nowrap">
              <Select
                data={spaces.map((space) => ({ label: space.name, value: space.id }))}
                disabled={!isReady || allSpaces}
                placeholder="Choose a Space"
                size="sm"
                value={activeSpace?.id ?? null}
                w={140}
                onChange={(value) => setActiveSpace(spaces.find((space) => space.id === value) ?? null)}
              />
              <Switch checked={allSpaces} label="All spaces" onChange={(event) => setAllSpaces(event.currentTarget.checked)} />
              <Badge color={allSpaces ? "blue" : "teal"} maw={180} variant="light" visibleFrom="lg">
                {allSpaces ? "Reading across all Spaces" : activeSpace?.name ?? "Single Space"}
              </Badge>
            </Group>

            <Group gap="sm" justify="flex-end" wrap="nowrap">
              <Stack gap={0} align="end" visibleFrom="sm">
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
          </Box>
        </Container>
      </AppShell.Header>
      <AppShell.Navbar p="md">
        <AppShell.Section>
          <Stack gap="xs">
            {primaryLinks.map((item) => (
              <NavLink
                key={item.to}
                active={isActivePath(pathname, item.to)}
                component={Link}
                label={item.label}
                to={item.to}
                variant="filled"
                onClick={close}
              />
            ))}
            {isAdmin ? (
              <NavLink
                active={isActivePath(pathname, "/admin")}
                color="red"
                component={Link}
                label="Admin"
                to="/admin"
                variant="light"
                onClick={close}
              />
            ) : null}
          </Stack>
        </AppShell.Section>
      </AppShell.Navbar>
      <AppShell.Main>
        <Container size="xl" py="xl">
          <Outlet />
        </Container>
      </AppShell.Main>
    </AppShell>
  );
}
