import { useEffect, useState, type FormEvent } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  Divider,
  Group,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Title
} from "@mantine/core";

import { ApiProblemError } from "../../../shared/api/client";
import { useSpaceScope } from "../../../shared/state/spaceScope";
import { archiveSpace, createSpace, updateSpace } from "../api/spacesApi";

interface SpaceDraft {
  description: string;
  name: string;
}

export function SpacesPage() {
  const {
    activeSpace,
    allSpaces,
    archivedSpaces,
    isReady,
    refreshSpaces,
    setActiveSpace,
    spaces
  } = useSpaceScope();
  const [createName, setCreateName] = useState("");
  const [createDescription, setCreateDescription] = useState("");
  const [drafts, setDrafts] = useState<Record<string, SpaceDraft>>({});
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [savingSpaceId, setSavingSpaceId] = useState<string | null>(null);

  useEffect(() => {
    setDrafts((currentDrafts) => {
      const nextDrafts: Record<string, SpaceDraft> = {};
      for (const space of [...spaces, ...archivedSpaces]) {
        nextDrafts[space.id] = currentDrafts[space.id] ?? {
          description: space.description ?? "",
          name: space.name
        };
      }
      return nextDrafts;
    });
  }, [archivedSpaces, spaces]);

  async function handleCreateSpace(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsCreating(true);
    setErrorMessage(null);
    try {
      await createSpace({
        description: createDescription || null,
        name: createName
      });
      setCreateDescription("");
      setCreateName("");
      await refreshSpaces();
    } catch (error) {
      if (error instanceof ApiProblemError) {
        setErrorMessage(error.problem.detail);
      } else {
        setErrorMessage("Unable to create the Space right now.");
      }
    } finally {
      setIsCreating(false);
    }
  }

  async function handleSpaceUpdate(spaceId: string, payload: Record<string, unknown>) {
    setSavingSpaceId(spaceId);
    setErrorMessage(null);
    try {
      const updated = await updateSpace(spaceId, payload);
      await refreshSpaces();
      if (updated.archived_at === null) {
        setActiveSpace(updated);
      }
    } catch (error) {
      if (error instanceof ApiProblemError) {
        setErrorMessage(error.problem.detail);
      } else {
        setErrorMessage("Unable to update the Space right now.");
      }
    } finally {
      setSavingSpaceId(null);
    }
  }

  async function handleArchiveSpace(spaceId: string) {
    setSavingSpaceId(spaceId);
    setErrorMessage(null);
    try {
      await archiveSpace(spaceId);
      await refreshSpaces();
    } catch (error) {
      if (error instanceof ApiProblemError) {
        setErrorMessage(error.problem.detail);
      } else {
        setErrorMessage("Unable to archive the Space right now.");
      }
    } finally {
      setSavingSpaceId(null);
    }
  }

  return (
    <Stack gap="xl">
      <Stack gap={4}>
        <Title order={2}>Spaces</Title>
        <Text c="dimmed">
          Organize documents by workspace and keep the current read scope explicit.
        </Text>
        {allSpaces ? (
          <Alert color="blue" title="All-spaces mode is on">
            Read views can span every Space right now. Actions that need one target Space should ask you to pick it explicitly.
          </Alert>
        ) : null}
      </Stack>

      {errorMessage ? (
        <Alert color="red" title="Space action failed">
          {errorMessage}
        </Alert>
      ) : null}

      <Card withBorder radius="lg" p="lg">
        <Stack gap="md">
          <Title order={4}>Create a Space</Title>
          <form onSubmit={handleCreateSpace}>
            <Stack gap="md">
              <TextInput
                required
                disabled={isCreating}
                label="Name"
                placeholder="Research workspace"
                value={createName}
                onChange={(event) => setCreateName(event.currentTarget.value)}
              />
              <TextInput
                disabled={isCreating}
                label="Description"
                placeholder="Optional note for the team"
                value={createDescription}
                onChange={(event) => setCreateDescription(event.currentTarget.value)}
              />
              <Button loading={isCreating} type="submit">
                Create Space
              </Button>
            </Stack>
          </form>
        </Stack>
      </Card>

      <Stack gap="md">
        <Group justify="space-between">
          <Title order={3}>Active Spaces</Title>
          <Badge variant="light">{isReady ? `${spaces.length} active` : "Loading"}</Badge>
        </Group>
        <SimpleGrid cols={{ base: 1, md: 2 }}>
          {spaces.map((space) => {
            const draft = drafts[space.id] ?? {
              description: space.description ?? "",
              name: space.name
            };

            return (
              <Card key={space.id} withBorder radius="lg" p="lg">
                <Stack gap="md">
                  <Group justify="space-between">
                    <Stack gap={0}>
                      <Title order={4}>{space.name}</Title>
                      <Text c="dimmed" size="sm">
                        {space.description || "No description"}
                      </Text>
                    </Stack>
                    <Group gap="xs">
                      {space.id === activeSpace?.id ? <Badge color="teal">active</Badge> : null}
                      {space.is_default ? <Badge variant="light">default</Badge> : null}
                    </Group>
                  </Group>

                  <TextInput
                    label="Name"
                    value={draft.name}
                    onChange={(event) =>
                      setDrafts((currentDrafts) => ({
                        ...currentDrafts,
                        [space.id]: {
                          ...draft,
                          name: event.currentTarget.value
                        }
                      }))
                    }
                  />
                  <TextInput
                    label="Description"
                    value={draft.description}
                    onChange={(event) =>
                      setDrafts((currentDrafts) => ({
                        ...currentDrafts,
                        [space.id]: {
                          ...draft,
                          description: event.currentTarget.value
                        }
                      }))
                    }
                  />

                  <Group>
                    <Button
                      loading={savingSpaceId === space.id}
                      variant="light"
                      onClick={() =>
                        void handleSpaceUpdate(space.id, {
                          description: draft.description || null,
                          name: draft.name
                        })
                      }
                    >
                      Save
                    </Button>
                    <Button variant="subtle" onClick={() => setActiveSpace(space)}>
                      Use as active Space
                    </Button>
                    {!space.is_default ? (
                      <Button
                        variant="subtle"
                        onClick={() => void handleSpaceUpdate(space.id, { is_default: true })}
                      >
                        Set as default
                      </Button>
                    ) : null}
                    {!space.is_default ? (
                      <Button color="red" variant="subtle" onClick={() => void handleArchiveSpace(space.id)}>
                        Archive
                      </Button>
                    ) : null}
                  </Group>
                </Stack>
              </Card>
            );
          })}
        </SimpleGrid>
      </Stack>

      <Divider />

      <Stack gap="md">
        <Group justify="space-between">
          <Title order={3}>Archived Spaces</Title>
          <Badge variant="light">{archivedSpaces.length} archived</Badge>
        </Group>
        {archivedSpaces.length === 0 ? (
          <Text c="dimmed">No archived Spaces yet.</Text>
        ) : (
          <SimpleGrid cols={{ base: 1, md: 2 }}>
            {archivedSpaces.map((space) => (
              <Card key={space.id} withBorder radius="lg" p="lg">
                <Stack gap="xs">
                  <Group justify="space-between">
                    <Title order={4}>{space.name}</Title>
                    <Badge color="gray">archived</Badge>
                  </Group>
                  <Text c="dimmed" size="sm">
                    {space.description || "No description"}
                  </Text>
                  <Text size="sm">Archived Spaces stay visible for read history but are not active upload targets.</Text>
                </Stack>
              </Card>
            ))}
          </SimpleGrid>
        )}
      </Stack>
    </Stack>
  );
}
