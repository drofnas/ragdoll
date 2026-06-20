import { Card, Stack, Text, Title } from "@mantine/core";

import { useAuthSession } from "../../../shared/state/authSession";
import { useSpaceScope } from "../../../shared/state/spaceScope";

export function DashboardPage() {
  const { currentUser, scaffoldMode } = useAuthSession();
  const { activeSpace, allSpaces } = useSpaceScope();

  return (
    <Card shadow="sm" padding="xl">
      <Stack gap="sm">
        <Title order={2}>Authenticated Dashboard Placeholder</Title>
        <Text>Scaffold mode: {scaffoldMode}</Text>
        <Text>Current user: {currentUser?.email ?? "anonymous"}</Text>
        <Text>All spaces: {String(allSpaces)}</Text>
        <Text>Active space: {activeSpace?.name ?? "none"}</Text>
      </Stack>
    </Card>
  );
}
