import type { PinnedFactCandidate, PinnedFactHistoryEntry } from "@contracts";
import { useEffect, useState } from "react";
import { Link, Navigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { Page, PageHeader } from "@/components/app/page";
import { StatusBadge } from "@/components/app/status-badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ApiProblemError } from "@/shared/api/client";
import { formatCitationLabel, formatDateTime } from "@/shared/lib/formatting";
import { useSpaceScope } from "@/shared/state/spaceScope";
import {
  acceptPinnedFactCandidate,
  readPinnedFact,
  readPinnedFactCandidates,
  readPinnedFactHistory,
  recheckPinnedFact,
  rejectPinnedFactCandidate,
  revertPinnedFactHistory,
  updatePinnedFact
} from "../api/pinnedFactsApi";

function valueLabel(valueText: string | null | undefined, valueJson: Record<string, unknown> | null | undefined) {
  return valueText ?? JSON.stringify(valueJson, null, 2) ?? "Not set";
}

function candidateValue(candidate: PinnedFactCandidate) {
  return valueLabel(candidate.proposed_value_text, candidate.proposed_value_json);
}

function historyValue(entry: PinnedFactHistoryEntry) {
  return valueLabel(entry.new_value_text, entry.new_value_json);
}

export function PinnedFactDetailPage() {
  const { factId } = useParams<{ factId: string }>();
  const { activeSpace, allSpaces, buildReadScopeParams } = useSpaceScope();
  const readScopeQuery = buildReadScopeParams();
  const writeScopeQuery = !allSpaces && activeSpace ? { space_id: activeSpace.id } : null;
  const writeDisabledReason = allSpaces
    ? "Choose one active Space before reviewing or editing pinned facts."
    : activeSpace === null
      ? "Choose an active Space before reviewing or editing pinned facts."
      : null;

  const [candidateDrafts, setCandidateDrafts] = useState<Record<string, string>>({});
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [manualValueKind, setManualValueKind] = useState<"json" | "text">("text");
  const [manualValueInput, setManualValueInput] = useState("");
  const [manualUpdateNote, setManualUpdateNote] = useState("");

  const detailQuery = useQuery({
    enabled: Boolean(factId),
    queryFn: () => readPinnedFact(factId!, readScopeQuery),
    queryKey: ["pinned-fact-detail", factId, readScopeQuery]
  });

  const candidatesQuery = useQuery({
    enabled: Boolean(factId),
    queryFn: () => readPinnedFactCandidates(factId!, readScopeQuery),
    queryKey: ["pinned-fact-candidates", factId, readScopeQuery]
  });

  const historyQuery = useQuery({
    enabled: Boolean(factId),
    queryFn: () => readPinnedFactHistory(factId!, readScopeQuery),
    queryKey: ["pinned-fact-history", factId, readScopeQuery]
  });

  useEffect(() => {
    setCandidateDrafts((current) => {
      const next = { ...current };
      for (const candidate of candidatesQuery.data?.items ?? []) {
        if (!(candidate.id in next)) {
          next[candidate.id] = candidateValue(candidate);
        }
      }
      return next;
    });
  }, [candidatesQuery.data]);

  useEffect(() => {
    if (!detailQuery.data || isEditing) {
      return;
    }
    setManualValueKind(detailQuery.data.value_kind === "json" ? "json" : "text");
    setManualValueInput(valueLabel(detailQuery.data.value_text, detailQuery.data.value_json));
  }, [detailQuery.data, isEditing]);

  if (!factId) {
    return <Navigate to="/pinned-facts" replace />;
  }

  async function refetchAll() {
    await Promise.all([detailQuery.refetch(), candidatesQuery.refetch(), historyQuery.refetch()]);
  }

  async function handleAccept(candidate: PinnedFactCandidate) {
    if (!writeScopeQuery) {
      setErrorMessage(writeDisabledReason);
      return;
    }
    setBusyAction(`accept-${candidate.id}`);
    setErrorMessage(null);
    setFeedbackMessage(null);
    try {
      const draft = candidateDrafts[candidate.id] ?? "";
      const currentValue = candidateValue(candidate) ?? "";
      const payload =
        draft.trim() !== currentValue.trim()
          ? candidate.proposed_value_kind === "json"
            ? {
                review_notes: "Accepted after edit.",
                value_json: JSON.parse(draft) as Record<string, unknown>,
                value_kind: "json" as const
              }
            : { review_notes: "Accepted after edit.", value_kind: "text" as const, value_text: draft }
          : { review_notes: "Accepted." };
      await acceptPinnedFactCandidate(candidate.id, payload, writeScopeQuery);
      setFeedbackMessage("Update accepted.");
      await refetchAll();
    } catch (error) {
      if (error instanceof SyntaxError) {
        setErrorMessage("JSON candidate edits must be valid JSON before acceptance.");
      } else if (error instanceof ApiProblemError) {
        setErrorMessage(error.problem.detail);
      } else {
        setErrorMessage("Unable to accept that candidate right now.");
      }
    } finally {
      setBusyAction(null);
    }
  }

  async function handleReject(candidate: PinnedFactCandidate) {
    if (!writeScopeQuery) {
      setErrorMessage(writeDisabledReason);
      return;
    }
    setBusyAction(`reject-${candidate.id}`);
    setErrorMessage(null);
    setFeedbackMessage(null);
    try {
      await rejectPinnedFactCandidate(candidate.id, { review_notes: "Rejected." }, writeScopeQuery);
      setFeedbackMessage("Update rejected. The current stored value was preserved.");
      await refetchAll();
    } catch (error) {
      if (error instanceof ApiProblemError) {
        setErrorMessage(error.problem.detail);
      } else {
        setErrorMessage("Unable to reject that candidate right now.");
      }
    } finally {
      setBusyAction(null);
    }
  }

  async function handleRecheck() {
    if (!writeScopeQuery) {
      setErrorMessage(writeDisabledReason);
      return;
    }
    setBusyAction("recheck");
    setErrorMessage(null);
    setFeedbackMessage(null);
    try {
      await recheckPinnedFact(factId, writeScopeQuery);
      setFeedbackMessage("Pinned fact rerun complete.");
      await refetchAll();
    } catch (error) {
      if (error instanceof ApiProblemError) {
        setErrorMessage(error.problem.detail);
      } else {
        setErrorMessage("Unable to rerun that fact right now.");
      }
    } finally {
      setBusyAction(null);
    }
  }

  async function handleSaveManualEdit() {
    if (!writeScopeQuery || !detailQuery.data) {
      setErrorMessage(writeDisabledReason);
      return;
    }
    setBusyAction("manual-edit");
    setErrorMessage(null);
    setFeedbackMessage(null);
    try {
      const payload =
        manualValueKind === "json"
          ? {
              update_note: manualUpdateNote.trim() || null,
              value_json: JSON.parse(manualValueInput) as Record<string, unknown>,
              value_kind: "json" as const
            }
          : {
              update_note: manualUpdateNote.trim() || null,
              value_kind: "text" as const,
              value_text: manualValueInput
            };
      await updatePinnedFact(factId, payload, writeScopeQuery);
      setIsEditing(false);
      setManualUpdateNote("");
      setFeedbackMessage("Stored value updated.");
      await refetchAll();
    } catch (error) {
      if (error instanceof SyntaxError) {
        setErrorMessage("JSON stored values must be valid JSON before saving.");
      } else if (error instanceof ApiProblemError) {
        setErrorMessage(error.problem.detail);
      } else {
        setErrorMessage("Unable to save that edit right now.");
      }
    } finally {
      setBusyAction(null);
    }
  }

  async function handleRevert(entry: PinnedFactHistoryEntry) {
    if (!writeScopeQuery) {
      setErrorMessage(writeDisabledReason);
      return;
    }
    setBusyAction(`revert-${entry.id}`);
    setErrorMessage(null);
    setFeedbackMessage(null);
    try {
      await revertPinnedFactHistory(factId, entry.id, writeScopeQuery);
      setFeedbackMessage("Pinned fact restored to that historical version.");
      await refetchAll();
    } catch (error) {
      if (error instanceof ApiProblemError) {
        setErrorMessage(error.problem.detail);
      } else {
        setErrorMessage("Unable to restore that pinned fact right now.");
      }
    } finally {
      setBusyAction(null);
    }
  }

  return (
    <Page>
      <PageHeader
        eyebrow="Pinned fact detail"
        title={detailQuery.data?.title ?? "Pinned fact"}
        description={detailQuery.data?.description}
        actions={detailQuery.data ? <StatusBadge value={detailQuery.data.status} /> : undefined}
      >
        <Button asChild variant="ghost">
          <Link to="/pinned-facts">Back to pinned facts</Link>
        </Button>
      </PageHeader>

      {writeDisabledReason ? (
        <Alert variant="info">
          <AlertTitle>Write actions are limited</AlertTitle>
          <AlertDescription>{writeDisabledReason}</AlertDescription>
        </Alert>
      ) : null}

      {errorMessage ? (
        <Alert variant="destructive">
          <AlertTitle>Pinned-fact action failed</AlertTitle>
          <AlertDescription>{errorMessage}</AlertDescription>
        </Alert>
      ) : null}

      {feedbackMessage ? (
        <Alert variant="success">
          <AlertTitle>Saved</AlertTitle>
          <AlertDescription>{feedbackMessage}</AlertDescription>
        </Alert>
      ) : null}

      {detailQuery.error instanceof ApiProblemError ? (
        <Alert variant="destructive">
          <AlertTitle>Unable to load the pinned fact</AlertTitle>
          <AlertDescription>{detailQuery.error.problem.detail}</AlertDescription>
        </Alert>
      ) : detailQuery.isLoading ? (
        <p className="text-sm text-muted-foreground">Loading pinned fact…</p>
      ) : detailQuery.data ? (
        <>
          {(detailQuery.data.status === "pending_update" ||
            detailQuery.data.status === "conflicted" ||
            detailQuery.data.status === "missing_evidence") && (
            <Alert variant={detailQuery.data.status === "missing_evidence" ? "destructive" : "info"}>
              <AlertTitle>
                {detailQuery.data.status === "pending_update"
                  ? "Pending update detected"
                  : detailQuery.data.status === "conflicted"
                    ? "Review conflicting updates"
                    : "Missing evidence warning"}
              </AlertTitle>
              <AlertDescription>
                {detailQuery.data.status === "pending_update"
                  ? "The current stored value remains active until you explicitly accept a proposed update."
                  : detailQuery.data.status === "conflicted"
                    ? "Multiple candidate values were found. Review and accept exactly the one you want to make current."
                    : "The current stored value remains visible, but the latest rerun did not find supporting evidence."}
              </AlertDescription>
            </Alert>
          )}

          <Card>
            <CardContent className="space-y-4 p-6">
              <div className="grid gap-4 md:grid-cols-3">
                <Card className="bg-background/65 shadow-none">
                  <CardContent className="space-y-2 p-4">
                    <p className="text-sm font-semibold">Current value</p>
                    <p className="whitespace-pre-wrap text-sm">
                      {valueLabel(detailQuery.data.value_text, detailQuery.data.value_json)}
                    </p>
                  </CardContent>
                </Card>
                <Card className="bg-background/65 shadow-none">
                  <CardContent className="space-y-2 p-4">
                    <p className="text-sm font-semibold">Updated by</p>
                    <p className="text-sm">
                      {detailQuery.data.updated_by?.full_name || detailQuery.data.updated_by?.email || "Unknown"}
                    </p>
                    <p className="text-xs text-muted-foreground">{formatDateTime(detailQuery.data.updated_at)}</p>
                  </CardContent>
                </Card>
                <Card className="bg-background/65 shadow-none">
                  <CardContent className="space-y-2 p-4">
                    <p className="text-sm font-semibold">Last rerun</p>
                    <p className="text-sm">{formatDateTime(detailQuery.data.last_checked_at)}</p>
                  </CardContent>
                </Card>
              </div>

              <div className="space-y-2">
                <p className="text-sm font-semibold">Current evidence</p>
                {detailQuery.data.evidence.length ? (
                  detailQuery.data.evidence.map((evidence, index) => (
                    <Card key={`${detailQuery.data.id}-evidence-${index}`} className="bg-background/65 shadow-none">
                      <CardContent className="space-y-2 p-4">
                        <p className="text-sm">{evidence.quote}</p>
                        {evidence.citations.map((citation, citationIndex) => (
                          <p key={`${detailQuery.data.id}-${index}-${citationIndex}`} className="text-sm text-muted-foreground">
                            {formatCitationLabel(citation)}
                          </p>
                        ))}
                      </CardContent>
                    </Card>
                  ))
                ) : (
                  <p className="text-sm text-muted-foreground">No evidence is attached to the current value.</p>
                )}
              </div>

              <div className="flex flex-wrap justify-end gap-3">
                <Button type="button" disabled={!writeScopeQuery} variant="outline" onClick={() => setIsEditing((current) => !current)}>
                  {isEditing ? "Cancel edit" : "Edit stored value"}
                </Button>
                <Button disabled={!writeScopeQuery} variant="outline" onClick={() => void handleRecheck()}>
                  {busyAction === "recheck" ? "Rerunning…" : "Rerun detection"}
                </Button>
              </div>

              {isEditing ? (
                <Card className="border-dashed">
                  <CardHeader>
                    <CardTitle className="text-base">Manual edit</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex gap-2">
                      <Button
                        type="button"
                        variant={manualValueKind === "text" ? "default" : "outline"}
                        onClick={() => setManualValueKind("text")}
                      >
                        Text
                      </Button>
                      <Button
                        type="button"
                        variant={manualValueKind === "json" ? "default" : "outline"}
                        onClick={() => setManualValueKind("json")}
                      >
                        JSON
                      </Button>
                    </div>
                    {manualValueKind === "json" ? (
                      <div className="space-y-2">
                        <label className="text-sm font-medium" htmlFor="manual-value-input">
                          Stored value
                        </label>
                        <Textarea
                          id="manual-value-input"
                          rows={8}
                          value={manualValueInput}
                          onChange={(event) => setManualValueInput(event.currentTarget.value)}
                        />
                      </div>
                    ) : (
                      <div className="space-y-2">
                        <label className="text-sm font-medium" htmlFor="manual-value-input">
                          Stored value
                        </label>
                        <Textarea
                          id="manual-value-input"
                          rows={5}
                          value={manualValueInput}
                          onChange={(event) => setManualValueInput(event.currentTarget.value)}
                        />
                      </div>
                    )}
                    <div className="space-y-2">
                      <label className="text-sm font-medium" htmlFor="manual-update-note">
                        Update note
                      </label>
                      <Textarea
                        id="manual-update-note"
                        rows={3}
                        placeholder="Optional context for this change"
                        value={manualUpdateNote}
                        onChange={(event) => setManualUpdateNote(event.currentTarget.value)}
                      />
                    </div>
                    <div className="flex justify-end">
                      <Button disabled={!writeScopeQuery} onClick={() => void handleSaveManualEdit()}>
                        {busyAction === "manual-edit" ? "Saving…" : "Save edit"}
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ) : null}
            </CardContent>
          </Card>

          <section className="space-y-4">
            <h2 className="text-2xl font-semibold tracking-tight">Pending updates</h2>
            {candidatesQuery.isLoading ? (
              <p className="text-sm text-muted-foreground">Loading pending updates…</p>
            ) : candidatesQuery.data?.items.filter((candidate) => candidate.status === "pending").length ? (
              candidatesQuery.data.items
                .filter((candidate) => candidate.status === "pending")
                .map((candidate) => (
                  <Card key={candidate.id}>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2 text-base">
                        Review update
                        <Badge variant="secondary">{candidate.change_type.replace("_", " ")}</Badge>
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="grid gap-4 lg:grid-cols-2">
                        <Card className="bg-background/65 shadow-none">
                          <CardContent className="space-y-2 p-4">
                            <p className="text-sm font-semibold">Current value</p>
                            <p className="whitespace-pre-wrap text-sm">
                              {valueLabel(detailQuery.data.value_text, detailQuery.data.value_json)}
                            </p>
                          </CardContent>
                        </Card>
                        <Card className="bg-background/65 shadow-none">
                          <CardContent className="space-y-2 p-4">
                            <p className="text-sm font-semibold">Proposed value</p>
                            {candidate.proposed_value_kind === "json" ? (
                              <Textarea
                                rows={8}
                                value={candidateDrafts[candidate.id] ?? ""}
                                onChange={(event) => {
                                  const nextValue = event.currentTarget.value;
                                  setCandidateDrafts((current) => ({ ...current, [candidate.id]: nextValue }));
                                }}
                              />
                            ) : (
                              <Input
                                value={candidateDrafts[candidate.id] ?? ""}
                                onChange={(event) => {
                                  const nextValue = event.currentTarget.value;
                                  setCandidateDrafts((current) => ({ ...current, [candidate.id]: nextValue }));
                                }}
                              />
                            )}
                          </CardContent>
                        </Card>
                      </div>

                      <div className="space-y-2">
                        <p className="text-sm font-semibold">Proposed evidence</p>
                        {candidate.evidence.map((evidence, index) => (
                          <Card key={`${candidate.id}-evidence-${index}`} className="bg-background/65 shadow-none">
                            <CardContent className="space-y-2 p-4">
                              <p className="text-sm">{evidence.quote}</p>
                              {evidence.citations.map((citation, citationIndex) => (
                                <p key={`${candidate.id}-${index}-${citationIndex}`} className="text-sm text-muted-foreground">
                                  {formatCitationLabel(citation)}
                                </p>
                              ))}
                            </CardContent>
                          </Card>
                        ))}
                      </div>

                      <div className="flex justify-end gap-3">
                        <Button disabled={!writeScopeQuery} variant="ghost" onClick={() => void handleReject(candidate)}>
                          {busyAction === `reject-${candidate.id}` ? "Rejecting…" : "Reject"}
                        </Button>
                        <Button disabled={!writeScopeQuery} onClick={() => void handleAccept(candidate)}>
                          {busyAction === `accept-${candidate.id}` ? "Accepting…" : "Accept update"}
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))
            ) : (
              <p className="text-sm text-muted-foreground">No pending updates are waiting for review.</p>
            )}
          </section>

          <section className="space-y-4">
            <h2 className="text-2xl font-semibold tracking-tight">History</h2>
            {historyQuery.isLoading ? (
              <p className="text-sm text-muted-foreground">Loading history…</p>
            ) : historyQuery.data?.items.length ? (
              historyQuery.data.items.map((entry) => (
                <Card key={entry.id}>
                  <CardContent className="flex flex-col gap-4 p-6 lg:flex-row lg:items-center lg:justify-between">
                    <div className="space-y-1">
                      <p className="font-medium">{historyValue(entry)}</p>
                      <p className="text-sm text-muted-foreground">
                        {entry.reason} · {formatDateTime(entry.created_at)}
                      </p>
                      {entry.update_note ? (
                        <p className="text-sm text-muted-foreground">{entry.update_note}</p>
                      ) : null}
                    </div>
                    <Button disabled={!writeScopeQuery} variant="outline" onClick={() => void handleRevert(entry)}>
                      {busyAction === `revert-${entry.id}` ? "Restoring…" : "Restore this version"}
                    </Button>
                  </CardContent>
                </Card>
              ))
            ) : (
              <p className="text-sm text-muted-foreground">No history is available for this pinned fact yet.</p>
            )}
          </section>
        </>
      ) : null}
    </Page>
  );
}
