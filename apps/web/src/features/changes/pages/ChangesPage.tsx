import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { Page, PageHeader } from "@/components/app/page";
import { SelectField } from "@/components/app/select-field";
import { StatusBadge } from "@/components/app/status-badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Pagination } from "@/components/ui/pagination";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { ApiProblemError } from "@/shared/api/client";
import {
  formatCitationLabel,
  formatDateTime,
  formatSourceTier
} from "@/shared/lib/formatting";
import { useSpaceScope } from "@/shared/state/spaceScope";
import {
  listChanges,
  listCorrections,
  markChangeRead,
  readChangeDetail,
  readCorrectionDetail,
  rejectCorrection,
  verifyCorrection
} from "../api/changesApi";

const CORRECTION_STATUS_OPTIONS = [
  { label: "All statuses", value: "" },
  { label: "Pending", value: "pending" },
  { label: "Verified", value: "verified" },
  { label: "Rejected", value: "rejected" }
];

export function ChangesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { buildReadScopeParams, isReady } = useSpaceScope();
  const [reviewNotes, setReviewNotes] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);
  const [isMarkingRead, setIsMarkingRead] = useState(false);
  const [reviewAction, setReviewAction] = useState<"verify" | "reject" | null>(null);

  const activeTab = searchParams.get("tab") === "corrections" ? "corrections" : "activity";
  const changeId = searchParams.get("change_id");
  const correctionId = searchParams.get("correction_id");
  const correctionStatus = searchParams.get("status") ?? "";
  const changePage = Math.max(1, Number(searchParams.get("changes_page") ?? "1") || 1);
  const correctionsPage = Math.max(
    1,
    Number(searchParams.get("corrections_page") ?? "1") || 1
  );
  const scopeQuery = buildReadScopeParams();

  function updateParams(updates: Record<string, string | null | undefined>) {
    const next = new URLSearchParams(searchParams);
    for (const [key, value] of Object.entries(updates)) {
      if (!value) {
        next.delete(key);
      } else {
        next.set(key, value);
      }
    }
    setSearchParams(next);
  }

  const changesQuery = useQuery({
    enabled: isReady,
    queryFn: () =>
      listChanges({
        page: changePage,
        page_size: 10,
        ...scopeQuery
      }),
    queryKey: ["changes", changePage, scopeQuery]
  });

  const changeDetailQuery = useQuery({
    enabled: Boolean(changeId),
    queryFn: () => readChangeDetail(changeId!),
    queryKey: ["change-detail", changeId]
  });

  const correctionsQuery = useQuery({
    enabled: isReady,
    queryFn: () =>
      listCorrections({
        page: correctionsPage,
        page_size: 10,
        status: correctionStatus || undefined,
        ...scopeQuery
      }),
    queryKey: ["corrections", correctionsPage, correctionStatus, scopeQuery]
  });

  const correctionDetailQuery = useQuery({
    enabled: Boolean(correctionId),
    queryFn: () => readCorrectionDetail(correctionId!),
    queryKey: ["correction-detail", correctionId]
  });

  async function handleMarkRead() {
    if (!changeId) {
      return;
    }

    setIsMarkingRead(true);
    setErrorMessage(null);
    setFeedbackMessage(null);
    try {
      await markChangeRead(changeId);
      setFeedbackMessage("Change marked as read.");
      await Promise.all([changesQuery.refetch(), changeDetailQuery.refetch()]);
    } catch (error) {
      if (error instanceof ApiProblemError) {
        setErrorMessage(error.problem.detail);
      } else {
        setErrorMessage("Unable to mark that change as read right now.");
      }
    } finally {
      setIsMarkingRead(false);
    }
  }

  async function handleReview(action: "verify" | "reject") {
    if (!correctionId) {
      return;
    }

    setReviewAction(action);
    setErrorMessage(null);
    setFeedbackMessage(null);
    try {
      if (action === "verify") {
        await verifyCorrection(correctionId, { review_notes: reviewNotes || null });
      } else {
        await rejectCorrection(correctionId, { review_notes: reviewNotes || null });
      }
      setFeedbackMessage(action === "verify" ? "Correction verified." : "Correction rejected.");
      await Promise.all([correctionsQuery.refetch(), correctionDetailQuery.refetch()]);
    } catch (error) {
      if (error instanceof ApiProblemError) {
        setErrorMessage(error.problem.detail);
      } else {
        setErrorMessage("Unable to review that correction right now.");
      }
    } finally {
      setReviewAction(null);
    }
  }

  return (
    <Page>
      <PageHeader
        eyebrow="Review hub"
        title="Changes"
        description="Review activity updates, inspect change details, and manage correction review from one place."
      />

      {errorMessage ? (
        <Alert variant="destructive">
          <AlertTitle>Changes action failed</AlertTitle>
          <AlertDescription>{errorMessage}</AlertDescription>
        </Alert>
      ) : null}

      {feedbackMessage ? (
        <Alert variant="success">
          <AlertTitle>Saved</AlertTitle>
          <AlertDescription>{feedbackMessage}</AlertDescription>
        </Alert>
      ) : null}

      <Tabs value={activeTab} onValueChange={(value) => updateParams({ tab: value ?? "activity" })}>
        <TabsList>
          <TabsTrigger value="activity">Activity</TabsTrigger>
          <TabsTrigger value="corrections">Corrections</TabsTrigger>
        </TabsList>

        <TabsContent value="activity">
          <section className="grid min-w-0 gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
            <Card className="min-w-0">
              <CardHeader className="flex flex-row items-center justify-between gap-4 space-y-0">
                <CardTitle>Activity feed</CardTitle>
                <Badge variant="outline">{changesQuery.data?.total ?? 0} events</Badge>
              </CardHeader>
              <CardContent className="space-y-4">
                {changesQuery.error instanceof ApiProblemError ? (
                  <Alert variant="destructive">
                    <AlertTitle>Unable to load changes</AlertTitle>
                    <AlertDescription>{changesQuery.error.problem.detail}</AlertDescription>
                  </Alert>
                ) : changesQuery.isLoading ? (
                  <p className="text-sm text-muted-foreground">Loading change events…</p>
                ) : changesQuery.data && changesQuery.data.items.length > 0 ? (
                  <>
                    <div className="space-y-3">
                      {changesQuery.data.items.map((item) => (
                        <Card
                          key={item.id}
                          className={`min-w-0 ${item.id === changeId ? "border-primary/40 bg-muted/20" : "shadow-none"}`}
                        >
                          <CardContent className="min-w-0 space-y-3 p-4">
                            <div className="flex min-w-0 items-start justify-between gap-4">
                              <div className="min-w-0 flex-1 space-y-2">
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  className="h-auto max-w-full justify-start whitespace-normal break-words px-0 py-0 text-left leading-snug"
                                  onClick={() => updateParams({ change_id: item.id, tab: "activity" })}
                                >
                                  {item.title}
                                </Button>
                                <p className="break-words text-sm text-muted-foreground">{item.summary}</p>
                              </div>
                              <div className="shrink-0">
                                <StatusBadge value={item.is_read ? "read" : "unread"} />
                              </div>
                            </div>
                            <p className="text-sm text-muted-foreground">
                              {formatDateTime(item.created_at)}
                            </p>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                    <Pagination
                      currentPage={changePage}
                      totalPages={Math.max(1, Math.ceil(changesQuery.data.total / changesQuery.data.page_size))}
                      onPageChange={(nextPage) => updateParams({ changes_page: String(nextPage) })}
                    />
                  </>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    No change events are available for this scope yet.
                  </p>
                )}
              </CardContent>
            </Card>

            <Card className="min-w-0">
              <CardHeader className="flex flex-row items-center justify-between gap-4 space-y-0">
                <CardTitle>Change detail</CardTitle>
                {changeDetailQuery.data ? (
                  <StatusBadge value={changeDetailQuery.data.is_read ? "read" : "unread"} />
                ) : null}
              </CardHeader>
              <CardContent className="space-y-4">
                {changeDetailQuery.error instanceof ApiProblemError ? (
                  <Alert variant="destructive">
                    <AlertTitle>Unable to load change detail</AlertTitle>
                    <AlertDescription>{changeDetailQuery.error.problem.detail}</AlertDescription>
                  </Alert>
                ) : changeDetailQuery.isLoading ? (
                  <p className="text-sm text-muted-foreground">Loading change detail…</p>
                ) : changeDetailQuery.data ? (
                  <>
                    <div className="space-y-3">
                      <h3 className="break-words text-lg font-semibold">{changeDetailQuery.data.title}</h3>
                      <p className="break-words">{changeDetailQuery.data.summary}</p>
                      <p className="text-sm text-muted-foreground">
                        Event type: {changeDetailQuery.data.event_type} ·{" "}
                        {formatDateTime(changeDetailQuery.data.created_at)}
                      </p>
                      {changeDetailQuery.data.payload ? (
                        <pre className="max-w-full overflow-x-auto rounded-md border bg-slate-950 p-4 text-sm text-slate-100">
                          {JSON.stringify(changeDetailQuery.data.payload, null, 2)}
                        </pre>
                      ) : null}
                    </div>
                    <div className="flex justify-end">
                      <Button variant="outline" onClick={() => void handleMarkRead()}>
                        {isMarkingRead ? "Marking…" : "Mark read"}
                      </Button>
                    </div>
                  </>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    Choose an activity item to inspect its detail.
                  </p>
                )}
              </CardContent>
            </Card>
          </section>
        </TabsContent>

        <TabsContent value="corrections">
          <section className="grid min-w-0 gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
            <Card className="min-w-0">
              <CardHeader className="flex flex-row items-center justify-between gap-4 space-y-0">
                <CardTitle>Corrections</CardTitle>
                <Badge variant="outline">{correctionsQuery.data?.total ?? 0} records</Badge>
              </CardHeader>
              <CardContent className="space-y-4">
                <SelectField
                  label="Status filter"
                  options={CORRECTION_STATUS_OPTIONS.map((option) => ({
                    ...option,
                    value: option.value || "__all__"
                  }))}
                  value={correctionStatus || "__all__"}
                  onValueChange={(value) =>
                    updateParams({
                      corrections_page: "1",
                      status: value === "__all__" ? "" : value
                    })
                  }
                />

                {correctionsQuery.error instanceof ApiProblemError ? (
                  <Alert variant="destructive">
                    <AlertTitle>Unable to load corrections</AlertTitle>
                    <AlertDescription>{correctionsQuery.error.problem.detail}</AlertDescription>
                  </Alert>
                ) : correctionsQuery.isLoading ? (
                  <p className="text-sm text-muted-foreground">Loading corrections…</p>
                ) : correctionsQuery.data && correctionsQuery.data.items.length > 0 ? (
                  <>
                    <div className="space-y-3">
                      {correctionsQuery.data.items.map((item) => (
                        <Card
                          key={item.id}
                          className={`min-w-0 ${item.id === correctionId ? "border-primary/40 bg-muted/20" : "shadow-none"}`}
                        >
                          <CardContent className="min-w-0 space-y-3 p-4">
                            <div className="flex min-w-0 items-start justify-between gap-4">
                              <div className="min-w-0 flex-1 space-y-2">
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  className="h-auto max-w-full justify-start whitespace-normal break-words px-0 py-0 text-left leading-snug"
                                  onClick={() => updateParams({ correction_id: item.id, tab: "corrections" })}
                                >
                                  {item.proposed_value}
                                </Button>
                                <p className="break-words text-sm text-muted-foreground">
                                  {item.rationale ?? "No rationale provided"}
                                </p>
                              </div>
                              <div className="shrink-0">
                                <StatusBadge value={item.status} />
                              </div>
                            </div>
                            <p className="text-sm text-muted-foreground">
                              {formatDateTime(item.created_at)}
                            </p>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                    <Pagination
                      currentPage={correctionsPage}
                      totalPages={Math.max(
                        1,
                        Math.ceil(correctionsQuery.data.total / correctionsQuery.data.page_size)
                      )}
                      onPageChange={(nextPage) => updateParams({ corrections_page: String(nextPage) })}
                    />
                  </>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    No corrections match the current scope and filter.
                  </p>
                )}
              </CardContent>
            </Card>

            <Card className="min-w-0">
              <CardHeader>
                <CardTitle>Correction detail</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {correctionDetailQuery.error instanceof ApiProblemError ? (
                  <Alert variant="destructive">
                    <AlertTitle>Unable to load correction detail</AlertTitle>
                    <AlertDescription>{correctionDetailQuery.error.problem.detail}</AlertDescription>
                  </Alert>
                ) : correctionDetailQuery.isLoading ? (
                  <p className="text-sm text-muted-foreground">Loading correction detail…</p>
                ) : correctionDetailQuery.data ? (
                  <>
                    <div className="space-y-3">
                      <div className="flex min-w-0 items-start justify-between gap-4">
                        <h3 className="min-w-0 flex-1 break-words text-lg font-semibold">
                          {correctionDetailQuery.data.proposed_value}
                        </h3>
                        <div className="shrink-0">
                          <StatusBadge value={correctionDetailQuery.data.status} />
                        </div>
                      </div>
                      <p className="break-words">{correctionDetailQuery.data.rationale ?? "No rationale provided."}</p>
                      <p className="text-sm text-muted-foreground">
                        Submitted {formatDateTime(correctionDetailQuery.data.created_at)}
                      </p>
                      <p className="break-words text-sm text-muted-foreground">
                        Citation: {formatCitationLabel(correctionDetailQuery.data.citation)} ·{" "}
                        {formatSourceTier(correctionDetailQuery.data.citation.source_tier)}
                      </p>
                    </div>

                    <div className="space-y-2">
                      <label className="text-sm font-medium" htmlFor="review-notes">
                        Review notes
                      </label>
                      <Textarea
                        id="review-notes"
                        rows={4}
                        value={reviewNotes}
                        onChange={(event) => setReviewNotes(event.currentTarget.value)}
                      />
                    </div>

                    <div className="flex justify-end gap-3">
                      <Button
                        variant="ghost"
                        className="text-destructive hover:text-destructive"
                        onClick={() => void handleReview("reject")}
                      >
                        {reviewAction === "reject" ? "Rejecting…" : "Reject"}
                      </Button>
                      <Button onClick={() => void handleReview("verify")}>
                        {reviewAction === "verify" ? "Verifying…" : "Verify"}
                      </Button>
                    </div>
                  </>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    Choose a correction to inspect and review it.
                  </p>
                )}
              </CardContent>
            </Card>
          </section>
        </TabsContent>
      </Tabs>
    </Page>
  );
}
