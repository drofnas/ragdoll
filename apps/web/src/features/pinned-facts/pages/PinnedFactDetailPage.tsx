import type { PinnedFactCandidate, PinnedFactHistoryEntry } from "@contracts";
import { useEffect, useState } from "react";
import { Link, Navigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { Page, PageHeader } from "@/components/app/page";
import { StatusBadge } from "@/components/app/status-badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
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
  revertPinnedFactHistory
} from "../api/pinnedFactsApi";

function candidateValue(candidate: PinnedFactCandidate) {
  return candidate.proposed_value_text ?? JSON.stringify(candidate.proposed_value_json);
}

function historyValue(entry: PinnedFactHistoryEntry) {
  return entry.new_value_text ?? JSON.stringify(entry.new_value_json);
}

export function PinnedFactDetailPage() {
  const { factId } = useParams<{ factId: string }>();
  const { activeSpace, allSpaces, buildReadScopeParams } = useSpaceScope();
  const readScopeQuery = buildReadScopeParams();
  const writeScopeQuery = !allSpaces && activeSpace ? { space_id: activeSpace.id } : null;
  const writeDisabledReason = allSpaces
    ? "Choose one active Space before reviewing or reverting pinned facts."
    : activeSpace === null
      ? "Choose an active Space before reviewing or reverting pinned facts."
      : null;

  const [candidateDrafts, setCandidateDrafts] = useState<Record<string, string>>({});
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);
  const [busyAction, setBusyAction] = useState<string | null>(null);

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
      setFeedbackMessage("Candidate accepted.");
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
      setFeedbackMessage("Candidate rejected.");
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
      setFeedbackMessage("Pinned fact rechecked.");
      await refetchAll();
    } catch (error) {
      if (error instanceof ApiProblemError) {
        setErrorMessage(error.problem.detail);
      } else {
        setErrorMessage("Unable to recheck that fact right now.");
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
      setFeedbackMessage("Pinned fact reverted to that historical version.");
      await refetchAll();
    } catch (error) {
      if (error instanceof ApiProblemError) {
        setErrorMessage(error.problem.detail);
      } else {
        setErrorMessage("Unable to revert that pinned fact right now.");
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
          <Card>
            <CardContent className="space-y-4 p-6">
              <div className="grid gap-4 md:grid-cols-3">
                <Card className="bg-background/65 shadow-none">
                  <CardContent className="space-y-2 p-4">
                    <p className="text-sm font-semibold">Current value</p>
                    <p className="text-sm">{detailQuery.data.value_text ?? JSON.stringify(detailQuery.data.value_json)}</p>
                  </CardContent>
                </Card>
                <Card className="bg-background/65 shadow-none">
                  <CardContent className="space-y-2 p-4">
                    <p className="text-sm font-semibold">Confidence</p>
                    <p className="text-sm">{detailQuery.data.confidence ?? "Unknown"}</p>
                  </CardContent>
                </Card>
                <Card className="bg-background/65 shadow-none">
                  <CardContent className="space-y-2 p-4">
                    <p className="text-sm font-semibold">Last checked</p>
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

              <div className="flex justify-end">
                <Button disabled={!writeScopeQuery} variant="outline" onClick={() => void handleRecheck()}>
                  {busyAction === "recheck" ? "Rechecking…" : "Recheck fact"}
                </Button>
              </div>
            </CardContent>
          </Card>

          <section className="space-y-4">
            <h2 className="text-2xl font-semibold tracking-tight">Pending candidates</h2>
            {candidatesQuery.isLoading ? (
              <p className="text-sm text-muted-foreground">Loading candidates…</p>
            ) : candidatesQuery.data?.items.length ? (
              candidatesQuery.data.items.map((candidate) => (
                <Card key={candidate.id}>
                  <CardHeader>
                    <CardTitle className="text-base">Candidate {candidate.change_type}</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex flex-wrap gap-2">
                      <StatusBadge value={candidate.status} />
                    </div>
                    {candidate.proposed_value_kind === "json" ? (
                      <Textarea
                        rows={5}
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
                    <div className="flex justify-end gap-3">
                      <Button
                        disabled={!writeScopeQuery}
                        variant="ghost"
                        onClick={() => void handleReject(candidate)}
                      >
                        {busyAction === `reject-${candidate.id}` ? "Rejecting…" : "Reject"}
                      </Button>
                      <Button disabled={!writeScopeQuery} onClick={() => void handleAccept(candidate)}>
                        {busyAction === `accept-${candidate.id}` ? "Accepting…" : "Accept"}
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))
            ) : (
              <p className="text-sm text-muted-foreground">No pending candidates are waiting for review.</p>
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
                    </div>
                    <Button disabled={!writeScopeQuery} variant="outline" onClick={() => void handleRevert(entry)}>
                      {busyAction === `revert-${entry.id}` ? "Reverting…" : "Restore this version"}
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
