import type { TrackedFieldDefinition, TrackedFieldSummary } from "@contracts";
import { useEffect, useState, type FormEvent } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  Group,
  SimpleGrid,
  Stack,
  Switch,
  Text,
  TextInput,
  Textarea,
  Title
} from "@mantine/core";
import { useQuery } from "@tanstack/react-query";

import { ApiProblemError } from "../../../shared/api/client";
import {
  formatCitationLabel,
  formatDateTime,
  formatSourceTier,
  humanizeLabel
} from "../../../shared/lib/formatting";
import { useSpaceScope } from "../../../shared/state/spaceScope";
import {
  createTrackedField,
  listTrackedFields,
  readTrackedConflicts,
  readTrackedSummary,
  recomputeTrackedField,
  updateTrackedField
} from "../api/trackedStateApi";

interface FieldDraft {
  entityTypeHint: string;
  isActive: boolean;
  label: string;
  prompt: string;
}

export function TrackedStatePage() {
  const { activeSpace, allSpaces, buildReadScopeParams, isReady } = useSpaceScope();
  const [drafts, setDrafts] = useState<Record<string, FieldDraft>>({});
  const [createKey, setCreateKey] = useState("");
  const [createLabel, setCreateLabel] = useState("");
  const [createPrompt, setCreatePrompt] = useState("");
  const [createEntityTypeHint, setCreateEntityTypeHint] = useState("");
  const [createIsActive, setCreateIsActive] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [savingFieldId, setSavingFieldId] = useState<string | null>(null);
  const [recomputingFieldId, setRecomputingFieldId] = useState<string | null>(null);

  const readScopeQuery = buildReadScopeParams();
  const writeScopeQuery =
    !allSpaces && activeSpace ? { space_id: activeSpace.id } : null;
  const writeDisabledReason = allSpaces
    ? "Choose one active Space before creating or editing tracked state."
    : activeSpace === null
      ? "Choose an active Space before creating or editing tracked state."
      : null;

  const fieldsQuery = useQuery({
    enabled: isReady,
    queryFn: () =>
      listTrackedFields({
        page: 1,
        page_size: 50,
        ...readScopeQuery
      }),
    queryKey: ["tracked-fields", readScopeQuery]
  });

  const summaryQuery = useQuery({
    enabled: isReady,
    queryFn: () => readTrackedSummary(readScopeQuery),
    queryKey: ["tracked-summary", readScopeQuery]
  });

  const conflictsQuery = useQuery({
    enabled: isReady,
    queryFn: () => readTrackedConflicts(readScopeQuery),
    queryKey: ["tracked-conflicts", readScopeQuery]
  });

  useEffect(() => {
    setDrafts((currentDrafts) => {
      const nextDrafts: Record<string, FieldDraft> = {};
      for (const field of fieldsQuery.data?.items ?? []) {
        nextDrafts[field.id] = currentDrafts[field.id] ?? {
          entityTypeHint: field.entity_type_hint ?? "",
          isActive: field.is_active,
          label: field.label,
          prompt: field.prompt
        };
      }
      return nextDrafts;
    });
  }, [fieldsQuery.data]);

  const summaryById = Object.fromEntries(
    (summaryQuery.data?.items ?? []).map((summary) => [summary.id, summary] as const)
  ) as Record<string, TrackedFieldSummary>;

  async function refetchAll() {
    await Promise.all([
      fieldsQuery.refetch(),
      summaryQuery.refetch(),
      conflictsQuery.refetch()
    ]);
  }

  async function handleCreateField(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!writeScopeQuery) {
      setErrorMessage(writeDisabledReason);
      return;
    }

    setErrorMessage(null);
    setFeedbackMessage(null);
    setIsCreating(true);

    try {
      await createTrackedField(
        {
          entity_type_hint: createEntityTypeHint || null,
          is_active: createIsActive,
          key: createKey,
          label: createLabel,
          prompt: createPrompt
        },
        writeScopeQuery
      );
      setCreateKey("");
      setCreateLabel("");
      setCreatePrompt("");
      setCreateEntityTypeHint("");
      setCreateIsActive(true);
      setFeedbackMessage("Tracked field created.");
      await refetchAll();
    } catch (error) {
      if (error instanceof ApiProblemError) {
        setErrorMessage(error.problem.detail);
      } else {
        setErrorMessage("Unable to create that tracked field right now.");
      }
    } finally {
      setIsCreating(false);
    }
  }

  async function handleSaveField(field: TrackedFieldDefinition) {
    const draft = drafts[field.id];
    if (!draft || !writeScopeQuery) {
      setErrorMessage(writeDisabledReason);
      return;
    }

    setSavingFieldId(field.id);
    setErrorMessage(null);
    setFeedbackMessage(null);
    try {
      await updateTrackedField(
        field.id,
        {
          entity_type_hint: draft.entityTypeHint || null,
          is_active: draft.isActive,
          label: draft.label,
          prompt: draft.prompt
        },
        writeScopeQuery
      );
      setFeedbackMessage("Tracked field updated.");
      await refetchAll();
    } catch (error) {
      if (error instanceof ApiProblemError) {
        setErrorMessage(error.problem.detail);
      } else {
        setErrorMessage("Unable to update that tracked field right now.");
      }
    } finally {
      setSavingFieldId(null);
    }
  }

  async function handleRecompute(fieldId: string) {
    if (!writeScopeQuery) {
      setErrorMessage(writeDisabledReason);
      return;
    }

    setRecomputingFieldId(fieldId);
    setErrorMessage(null);
    setFeedbackMessage(null);
    try {
      await recomputeTrackedField(fieldId, writeScopeQuery);
      setFeedbackMessage("Tracked field recomputed.");
      await refetchAll();
    } catch (error) {
      if (error instanceof ApiProblemError) {
        setErrorMessage(error.problem.detail);
      } else {
        setErrorMessage("Unable to recompute that field right now.");
      }
    } finally {
      setRecomputingFieldId(null);
    }
  }

  return (
    <Stack gap="xl">
      <Stack gap={4}>
        <Title order={2}>Tracked state</Title>
        <Text c="dimmed">
          Define current-state questions, review resolution status, and inspect conflicts in the current scope.
        </Text>
        {writeDisabledReason ? (
          <Alert color="blue" title="Write actions are limited">
            {writeDisabledReason}
          </Alert>
        ) : null}
      </Stack>

      {errorMessage ? (
        <Alert color="red" title="Tracked-state action failed">
          {errorMessage}
        </Alert>
      ) : null}

      {feedbackMessage ? (
        <Alert color="teal" title="Saved">
          {feedbackMessage}
        </Alert>
      ) : null}

      <Card withBorder radius="lg" p="lg">
        <Stack gap="md">
          <Title order={4}>Create tracked field</Title>
          <form onSubmit={handleCreateField}>
            <Stack gap="md">
              <SimpleGrid cols={{ base: 1, md: 2 }}>
                <TextInput
                  required
                  disabled={!writeScopeQuery || isCreating}
                  label="Key"
                  placeholder="current_backend_framework"
                  value={createKey}
                  onChange={(event) => setCreateKey(event.currentTarget.value)}
                />
                <TextInput
                  required
                  disabled={!writeScopeQuery || isCreating}
                  label="Label"
                  placeholder="Current backend framework"
                  value={createLabel}
                  onChange={(event) => setCreateLabel(event.currentTarget.value)}
                />
              </SimpleGrid>
              <Textarea
                required
                disabled={!writeScopeQuery || isCreating}
                label="Prompt"
                minRows={2}
                placeholder="What is the current backend framework in this codebase?"
                value={createPrompt}
                onChange={(event) => setCreatePrompt(event.currentTarget.value)}
              />
              <SimpleGrid cols={{ base: 1, md: 2 }}>
                <TextInput
                  disabled={!writeScopeQuery || isCreating}
                  label="Entity type hint"
                  placeholder="Optional entity type"
                  value={createEntityTypeHint}
                  onChange={(event) => setCreateEntityTypeHint(event.currentTarget.value)}
                />
                <Switch
                  checked={createIsActive}
                  disabled={!writeScopeQuery || isCreating}
                  label="Active"
                  mt="xl"
                  onChange={(event) => setCreateIsActive(event.currentTarget.checked)}
                />
              </SimpleGrid>
              <Group justify="flex-end">
                <Button disabled={!writeScopeQuery} loading={isCreating} type="submit">
                  Create field
                </Button>
              </Group>
            </Stack>
          </form>
        </Stack>
      </Card>

      {fieldsQuery.error instanceof ApiProblemError ? (
        <Alert color="red" title="Unable to load tracked fields">
          {fieldsQuery.error.problem.detail}
        </Alert>
      ) : fieldsQuery.isLoading ? (
        <Text c="dimmed">Loading tracked fields…</Text>
      ) : (
        <Stack gap="md">
          <Group justify="space-between">
            <Title order={3}>Field summaries</Title>
            <Badge variant="light">{fieldsQuery.data?.total ?? 0} fields</Badge>
          </Group>
          {fieldsQuery.data?.items.length ? (
            fieldsQuery.data.items.map((field) => {
              const draft = drafts[field.id] ?? {
                entityTypeHint: field.entity_type_hint ?? "",
                isActive: field.is_active,
                label: field.label,
                prompt: field.prompt
              };
              const summary = summaryById[field.id];

              return (
                <Card key={field.id} withBorder radius="lg" p="lg">
                  <Stack gap="md">
                    <Group justify="space-between" align="start">
                      <Stack gap={2}>
                        <Title order={4}>{field.label}</Title>
                        <Text c="dimmed" size="sm">
                          {field.key}
                        </Text>
                      </Stack>
                      <Group gap="xs">
                        <Badge color={field.is_active ? "teal" : "gray"} variant="light">
                          {field.is_active ? "active" : "inactive"}
                        </Badge>
                        {summary ? (
                          <Badge variant="dot">{humanizeLabel(summary.status)}</Badge>
                        ) : null}
                      </Group>
                    </Group>

                    <SimpleGrid cols={{ base: 1, lg: 2 }}>
                      <Stack gap="sm">
                        <TextInput
                          label="Label"
                          value={draft.label}
                          onChange={(event) => {
                            const value = event.currentTarget.value;
                            return (
                            setDrafts((currentDrafts) => ({
                              ...currentDrafts,
                              [field.id]: {
                                ...draft,
                                label: value
                              }
                            }))
                            );
                          }}
                        />
                        <Textarea
                          label="Prompt"
                          minRows={2}
                          value={draft.prompt}
                          onChange={(event) => {
                            const value = event.currentTarget.value;
                            return (
                            setDrafts((currentDrafts) => ({
                              ...currentDrafts,
                              [field.id]: {
                                ...draft,
                                prompt: value
                              }
                            }))
                            );
                          }}
                        />
                      </Stack>

                      <Stack gap="sm">
                        <TextInput
                          label="Entity type hint"
                          value={draft.entityTypeHint}
                          onChange={(event) => {
                            const value = event.currentTarget.value;
                            return (
                            setDrafts((currentDrafts) => ({
                              ...currentDrafts,
                              [field.id]: {
                                ...draft,
                                entityTypeHint: value
                              }
                            }))
                            );
                          }}
                        />
                        <Switch
                          checked={draft.isActive}
                          label="Active"
                          onChange={(event) => {
                            const value = event.currentTarget.checked;
                            return (
                            setDrafts((currentDrafts) => ({
                              ...currentDrafts,
                              [field.id]: {
                                ...draft,
                                isActive: value
                              }
                            }))
                            );
                          }}
                        />
                        <Text c="dimmed" size="sm">
                          Last updated {formatDateTime(field.updated_at)}
                        </Text>
                      </Stack>
                    </SimpleGrid>

                    {summary ? (
                      <SimpleGrid cols={{ base: 1, md: 3 }}>
                        <Card withBorder radius="md" p="sm">
                          <Stack gap={2}>
                            <Text fw={600}>Current value</Text>
                            <Text>{summary.current_value ?? "Not resolved yet"}</Text>
                          </Stack>
                        </Card>
                        <Card withBorder radius="md" p="sm">
                          <Stack gap={2}>
                            <Text fw={600}>Source tier</Text>
                            <Text>{formatSourceTier(summary.current_source_tier)}</Text>
                          </Stack>
                        </Card>
                        <Card withBorder radius="md" p="sm">
                          <Stack gap={2}>
                            <Text fw={600}>Pending work</Text>
                            <Text>
                              {summary.conflict_count ?? 0} conflicts · {summary.pending_correction_count ?? 0} pending corrections
                            </Text>
                          </Stack>
                        </Card>
                      </SimpleGrid>
                    ) : null}

                    <Group justify="flex-end">
                      <Button
                        disabled={!writeScopeQuery}
                        loading={recomputingFieldId === field.id}
                        variant="subtle"
                        onClick={() => void handleRecompute(field.id)}
                      >
                        Recompute
                      </Button>
                      <Button
                        disabled={!writeScopeQuery}
                        loading={savingFieldId === field.id}
                        onClick={() => void handleSaveField(field)}
                      >
                        Save changes
                      </Button>
                    </Group>
                  </Stack>
                </Card>
              );
            })
          ) : (
            <Text c="dimmed">No tracked fields are configured for this scope yet.</Text>
          )}
        </Stack>
      )}

      <Stack gap="md">
        <Group justify="space-between">
          <Title order={3}>Conflicts</Title>
          <Badge variant="light">{conflictsQuery.data?.items.length ?? 0} conflicts</Badge>
        </Group>
        {conflictsQuery.error instanceof ApiProblemError ? (
          <Alert color="red" title="Unable to load tracked conflicts">
            {conflictsQuery.error.problem.detail}
          </Alert>
        ) : conflictsQuery.isLoading ? (
          <Text c="dimmed">Loading conflicts…</Text>
        ) : conflictsQuery.data && conflictsQuery.data.items.length > 0 ? (
          conflictsQuery.data.items.map((conflict) => (
            <Card key={conflict.field.id} withBorder radius="lg" p="lg">
              <Stack gap="md">
                <Group justify="space-between">
                  <Stack gap={2}>
                    <Title order={4}>{conflict.field.label}</Title>
                    <Text c="dimmed" size="sm">
                      {conflict.field.prompt}
                    </Text>
                  </Stack>
                  <Badge color="yellow" variant="light">
                    {humanizeLabel(conflict.status)}
                  </Badge>
                </Group>

                {conflict.candidates?.map((candidate, index) => (
                  <Card key={`${conflict.field.id}-${index}`} withBorder radius="md" p="sm">
                    <Stack gap={4}>
                      <Text fw={600}>{candidate.value_text}</Text>
                      <Text size="sm">
                        {formatSourceTier(candidate.source_tier)} · {candidate.status}
                      </Text>
                      <Text c="dimmed" size="sm">
                        {formatDateTime(candidate.created_at)}
                      </Text>
                      {candidate.citations?.map((citation, citationIndex) => (
                        <Text key={`${conflict.field.id}-${index}-${citationIndex}`} size="sm">
                          {formatCitationLabel(citation)}
                        </Text>
                      ))}
                    </Stack>
                  </Card>
                ))}
              </Stack>
            </Card>
          ))
        ) : (
          <Text c="dimmed">No tracked-state conflicts are present in the current scope.</Text>
        )}
      </Stack>
    </Stack>
  );
}
