import type { TrackedFieldDefinition, TrackedFieldSummary } from "@contracts";
import { useEffect, useState, type FormEvent } from "react";
import { useQuery } from "@tanstack/react-query";

import { Page, PageHeader } from "@/components/app/page";
import { StatusBadge } from "@/components/app/status-badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { ApiProblemError } from "@/shared/api/client";
import {
  formatCitationLabel,
  formatDateTime,
  formatSourceTier,
  humanizeLabel
} from "@/shared/lib/formatting";
import { useSpaceScope } from "@/shared/state/spaceScope";
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
  const writeScopeQuery = !allSpaces && activeSpace ? { space_id: activeSpace.id } : null;
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
    await Promise.all([fieldsQuery.refetch(), summaryQuery.refetch(), conflictsQuery.refetch()]);
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
    <Page>
      <PageHeader
        eyebrow="Resolution state"
        title="Tracked state"
        description="Define current-state questions, review resolution status, and inspect conflicts in the current scope."
      />

      {writeDisabledReason ? (
        <Alert variant="info">
          <AlertTitle>Write actions are limited</AlertTitle>
          <AlertDescription>{writeDisabledReason}</AlertDescription>
        </Alert>
      ) : null}

      {errorMessage ? (
        <Alert variant="destructive">
          <AlertTitle>Tracked-state action failed</AlertTitle>
          <AlertDescription>{errorMessage}</AlertDescription>
        </Alert>
      ) : null}

      {feedbackMessage ? (
        <Alert variant="success">
          <AlertTitle>Saved</AlertTitle>
          <AlertDescription>{feedbackMessage}</AlertDescription>
        </Alert>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Create tracked field</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="space-y-5" onSubmit={handleCreateField}>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="tracked-field-key">
                  Key
                </label>
                <Input
                  id="tracked-field-key"
                  required
                  disabled={!writeScopeQuery || isCreating}
                  placeholder="current_backend_framework"
                  value={createKey}
                  onChange={(event) => setCreateKey(event.currentTarget.value)}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="tracked-field-label">
                  Label
                </label>
                <Input
                  id="tracked-field-label"
                  required
                  disabled={!writeScopeQuery || isCreating}
                  placeholder="Current backend framework"
                  value={createLabel}
                  onChange={(event) => setCreateLabel(event.currentTarget.value)}
                />
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="tracked-field-prompt">
                Prompt
              </label>
              <Textarea
                id="tracked-field-prompt"
                required
                disabled={!writeScopeQuery || isCreating}
                rows={3}
                placeholder="What is the current backend framework in this codebase?"
                value={createPrompt}
                onChange={(event) => setCreatePrompt(event.currentTarget.value)}
              />
            </div>
            <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_auto] md:items-end">
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="tracked-field-entity-type">
                  Entity type hint
                </label>
                <Input
                  id="tracked-field-entity-type"
                  disabled={!writeScopeQuery || isCreating}
                  placeholder="Optional entity type"
                  value={createEntityTypeHint}
                  onChange={(event) => setCreateEntityTypeHint(event.currentTarget.value)}
                />
              </div>
              <label className="flex items-center gap-3 rounded-md border bg-muted/20 px-3 py-2">
                <Switch
                  checked={createIsActive}
                  disabled={!writeScopeQuery || isCreating}
                  onCheckedChange={(checked) => setCreateIsActive(Boolean(checked))}
                />
                <span className="text-sm font-medium">Active</span>
              </label>
            </div>
            <div className="flex justify-end">
              <Button disabled={!writeScopeQuery} type="submit">
                {isCreating ? "Creating…" : "Create field"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {fieldsQuery.error instanceof ApiProblemError ? (
        <Alert variant="destructive">
          <AlertTitle>Unable to load tracked fields</AlertTitle>
          <AlertDescription>{fieldsQuery.error.problem.detail}</AlertDescription>
        </Alert>
      ) : fieldsQuery.isLoading ? (
        <p className="text-sm text-muted-foreground">Loading tracked fields…</p>
      ) : (
        <section className="space-y-4">
          <div className="flex items-center justify-between gap-4">
            <h2 className="text-2xl font-semibold tracking-tight">Field summaries</h2>
            <Badge variant="outline">{fieldsQuery.data?.total ?? 0} fields</Badge>
          </div>
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
                <Card key={field.id}>
                  <CardContent className="space-y-5 p-6">
                    <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                      <div className="space-y-1">
                        <h3 className="text-lg font-semibold">{field.label}</h3>
                        <p className="text-sm text-muted-foreground">{field.key}</p>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <StatusBadge
                          label={field.is_active ? "Active" : "Inactive"}
                          value={field.is_active ? "active" : "inactive"}
                        />
                        {summary ? <StatusBadge value={summary.status} /> : null}
                      </div>
                    </div>

                    <div className="grid gap-4 lg:grid-cols-2">
                      <div className="space-y-4">
                        <div className="space-y-2">
                          <label className="text-sm font-medium">Label</label>
                        <Input
                          value={draft.label}
                          onChange={(event) => {
                            const nextValue = event.currentTarget.value;
                            return (
                              setDrafts((currentDrafts) => ({
                                ...currentDrafts,
                                [field.id]: {
                                  ...draft,
                                  label: nextValue
                                }
                              }))
                            );
                          }}
                        />
                        </div>
                        <div className="space-y-2">
                          <label className="text-sm font-medium">Prompt</label>
                        <Textarea
                          rows={4}
                          value={draft.prompt}
                          onChange={(event) => {
                            const nextValue = event.currentTarget.value;
                            return (
                              setDrafts((currentDrafts) => ({
                                ...currentDrafts,
                                [field.id]: {
                                  ...draft,
                                  prompt: nextValue
                                }
                              }))
                            );
                          }}
                        />
                        </div>
                      </div>

                      <div className="space-y-4">
                        <div className="space-y-2">
                          <label className="text-sm font-medium">Entity type hint</label>
                        <Input
                          value={draft.entityTypeHint}
                          onChange={(event) => {
                            const nextValue = event.currentTarget.value;
                            return (
                              setDrafts((currentDrafts) => ({
                                ...currentDrafts,
                                [field.id]: {
                                  ...draft,
                                  entityTypeHint: nextValue
                                }
                              }))
                            );
                          }}
                        />
                        </div>
                        <label className="flex items-center justify-between gap-4 rounded-md border bg-muted/20 px-3 py-2">
                          <span className="text-sm font-medium">Active</span>
                          <Switch
                            checked={draft.isActive}
                            onCheckedChange={(checked) =>
                              setDrafts((currentDrafts) => ({
                                ...currentDrafts,
                                [field.id]: {
                                  ...draft,
                                  isActive: Boolean(checked)
                                }
                              }))
                            }
                          />
                        </label>
                        <p className="text-sm text-muted-foreground">
                          Last updated {formatDateTime(field.updated_at)}
                        </p>
                      </div>
                    </div>

                    {summary ? (
                      <div className="grid gap-4 md:grid-cols-3">
                        <Card className="bg-background/65 shadow-none">
                          <CardContent className="space-y-2 p-5">
                            <p className="text-sm font-semibold">Current value</p>
                            <p>{summary.current_value ?? "Not resolved yet"}</p>
                          </CardContent>
                        </Card>
                        <Card className="bg-background/65 shadow-none">
                          <CardContent className="space-y-2 p-5">
                            <p className="text-sm font-semibold">Source tier</p>
                            <p>{formatSourceTier(summary.current_source_tier)}</p>
                          </CardContent>
                        </Card>
                        <Card className="bg-background/65 shadow-none">
                          <CardContent className="space-y-2 p-5">
                            <p className="text-sm font-semibold">Pending work</p>
                            <p>
                              {summary.conflict_count ?? 0} conflicts ·{" "}
                              {summary.pending_correction_count ?? 0} pending corrections
                            </p>
                          </CardContent>
                        </Card>
                      </div>
                    ) : null}

                    <div className="flex justify-end gap-3">
                      <Button
                        disabled={!writeScopeQuery}
                        variant="ghost"
                        onClick={() => void handleRecompute(field.id)}
                      >
                        {recomputingFieldId === field.id ? "Recomputing…" : "Recompute"}
                      </Button>
                      <Button
                        disabled={!writeScopeQuery}
                        onClick={() => void handleSaveField(field)}
                      >
                        {savingFieldId === field.id ? "Saving…" : "Save changes"}
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              );
            })
          ) : (
            <p className="text-sm text-muted-foreground">
              No tracked fields are configured for this scope yet.
            </p>
          )}
        </section>
      )}

      <section className="space-y-4">
        <div className="flex items-center justify-between gap-4">
          <h2 className="text-2xl font-semibold tracking-tight">Conflicts</h2>
          <Badge variant="outline">{conflictsQuery.data?.items.length ?? 0} conflicts</Badge>
        </div>
        {conflictsQuery.error instanceof ApiProblemError ? (
          <Alert variant="destructive">
            <AlertTitle>Unable to load tracked conflicts</AlertTitle>
            <AlertDescription>{conflictsQuery.error.problem.detail}</AlertDescription>
          </Alert>
        ) : conflictsQuery.isLoading ? (
          <p className="text-sm text-muted-foreground">Loading conflicts…</p>
        ) : conflictsQuery.data && conflictsQuery.data.items.length > 0 ? (
          conflictsQuery.data.items.map((conflict) => (
            <Card key={conflict.field.id}>
              <CardContent className="space-y-5 p-6">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div className="space-y-1">
                    <h3 className="text-lg font-semibold">{conflict.field.label}</h3>
                    <p className="text-sm text-muted-foreground">{conflict.field.prompt}</p>
                  </div>
                  <StatusBadge value={conflict.status} label={humanizeLabel(conflict.status)} />
                </div>

                <div className="space-y-3">
                  {conflict.candidates?.map((candidate, index) => (
                    <Card key={`${conflict.field.id}-${index}`} className="bg-background/65 shadow-none">
                      <CardContent className="space-y-2 p-5">
                        <p className="font-semibold">{candidate.value_text}</p>
                        <p className="text-sm text-muted-foreground">
                          {formatSourceTier(candidate.source_tier)} · {candidate.status}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          {formatDateTime(candidate.created_at)}
                        </p>
                        {candidate.citations?.map((citation, citationIndex) => (
                          <p
                            key={`${conflict.field.id}-${index}-${citationIndex}`}
                            className="text-sm text-muted-foreground"
                          >
                            {formatCitationLabel(citation)}
                          </p>
                        ))}
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))
        ) : (
          <p className="text-sm text-muted-foreground">
            No tracked-state conflicts are present in the current scope.
          </p>
        )}
      </section>
    </Page>
  );
}
