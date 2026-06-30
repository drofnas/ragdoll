import type {
  ChangeEventDetail,
  ChangeEventSummary,
  ChangeListResponse,
  CorrectionListResponse,
  CorrectionRecordResponse
} from "@contracts";
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { Page, PageHeader } from "@/components/app/page";
import { SelectField } from "@/components/app/select-field";
import { StatusBadge } from "@/components/app/status-badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger
} from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
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

interface ReviewActionState {
  action: "verify" | "reject";
  correctionId: string;
}

function addIdToSet(current: Set<string>, id: string) {
  if (current.has(id)) {
    return current;
  }
  const next = new Set(current);
  next.add(id);
  return next;
}

function markChangeIdsReadInList(current: ChangeListResponse | undefined, changeIds: Set<string>) {
  return current
    ? {
        ...current,
        items: current.items.map((item) =>
          changeIds.has(item.id) ? { ...item, is_read: true } : item
        )
      }
    : current;
}

export function ChangesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const { buildReadScopeParams, isReady } = useSpaceScope();

  const activeTab = searchParams.get("tab") === "corrections" ? "corrections" : "activity";
  const changeId = searchParams.get("change_id");
  const correctionId = searchParams.get("correction_id");
  const correctionStatus = searchParams.get("status") ?? "";
  const changePage = Math.max(1, Number(searchParams.get("changes_page") ?? "1") || 1);
  const correctionsPage = Math.max(
    1,
    Number(searchParams.get("corrections_page") ?? "1") || 1
  );

  const [reviewNotesById, setReviewNotesById] = useState<Record<string, string>>({});
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);
  const [markingReadId, setMarkingReadId] = useState<string | null>(null);
  const [isMarkingAllRead, setIsMarkingAllRead] = useState(false);
  const [reviewAction, setReviewAction] = useState<ReviewActionState | null>(null);
  const [loadedChangeIds, setLoadedChangeIds] = useState(
    () => new Set<string>(changeId ? [changeId] : [])
  );
  const [loadedCorrectionIds, setLoadedCorrectionIds] = useState(
    () => new Set<string>(correctionId ? [correctionId] : [])
  );
  const [expandedChangeId, setExpandedChangeId] = useState(changeId ?? "");
  const [expandedCorrectionId, setExpandedCorrectionId] = useState(correctionId ?? "");

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

  function rememberLoadedChangeId(id: string) {
    setLoadedChangeIds((current) => addIdToSet(current, id));
  }

  function rememberLoadedCorrectionId(id: string) {
    setLoadedCorrectionIds((current) => addIdToSet(current, id));
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
  const unreadVisibleChangeIds = (changesQuery.data?.items ?? [])
    .filter((item) => !item.is_read)
    .map((item) => item.id);

  useEffect(() => {
    if (changeId) {
      rememberLoadedChangeId(changeId);
    }
  }, [changeId]);

  useEffect(() => {
    if (correctionId) {
      rememberLoadedCorrectionId(correctionId);
    }
  }, [correctionId]);

  useEffect(() => {
    setExpandedChangeId(changeId ?? "");
  }, [changeId]);

  useEffect(() => {
    setExpandedCorrectionId(correctionId ?? "");
  }, [correctionId]);

  useEffect(() => {
    if (!expandedChangeId || !changesQuery.data) {
      return;
    }
    if (!changesQuery.data.items.some((item) => item.id === expandedChangeId)) {
      setExpandedChangeId("");
      if (changeId) {
        updateParams({ change_id: null });
      }
    }
  }, [changeId, changesQuery.data, expandedChangeId]);

  useEffect(() => {
    if (!expandedCorrectionId || !correctionsQuery.data) {
      return;
    }
    if (!correctionsQuery.data.items.some((item) => item.id === expandedCorrectionId)) {
      setExpandedCorrectionId("");
      if (correctionId) {
        updateParams({ correction_id: null });
      }
    }
  }, [correctionId, correctionsQuery.data, expandedCorrectionId]);

  async function handleMarkRead(targetChangeId: string) {
    setMarkingReadId(targetChangeId);
    setErrorMessage(null);
    setFeedbackMessage(null);
    try {
      await markChangeRead(targetChangeId);
      setFeedbackMessage("Change marked as read.");
      queryClient.setQueryData<ChangeEventDetail>(
        ["change-detail", targetChangeId],
        (current) => (current ? { ...current, is_read: true } : current)
      );
      queryClient.setQueriesData<ChangeListResponse>(
        { queryKey: ["changes"] },
        (current) => markChangeIdsReadInList(current, new Set([targetChangeId]))
      );
    } catch (error) {
      if (error instanceof ApiProblemError) {
        setErrorMessage(error.problem.detail);
      } else {
        setErrorMessage("Unable to mark that change as read right now.");
      }
    } finally {
      setMarkingReadId(null);
    }
  }

  async function handleMarkAllRead() {
    if (unreadVisibleChangeIds.length === 0) {
      return;
    }
    const targetIds = [...unreadVisibleChangeIds];
    const targetIdSet = new Set(targetIds);
    setIsMarkingAllRead(true);
    setErrorMessage(null);
    setFeedbackMessage(null);
    try {
      await Promise.all(targetIds.map((changeId) => markChangeRead(changeId)));
      setFeedbackMessage("All visible changes marked as read.");
      await Promise.all(
        targetIds.map((changeId) =>
          queryClient.setQueryData<ChangeEventDetail>(
            ["change-detail", changeId],
            (current) => (current ? { ...current, is_read: true } : current)
          )
        )
      );
      queryClient.setQueriesData<ChangeListResponse>(
        { queryKey: ["changes"] },
        (current) => markChangeIdsReadInList(current, targetIdSet)
      );
    } catch (error) {
      setErrorMessage("Unable to mark the visible changes as read right now.");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["changes"] }),
        ...targetIds.map((changeId) =>
          queryClient.invalidateQueries({ queryKey: ["change-detail", changeId] })
        )
      ]);
    } finally {
      setIsMarkingAllRead(false);
    }
  }

  async function handleReview(targetCorrectionId: string, action: "verify" | "reject") {
    setReviewAction({ action, correctionId: targetCorrectionId });
    setErrorMessage(null);
    setFeedbackMessage(null);
    try {
      const reviewNotes = reviewNotesById[targetCorrectionId] || null;
      const updatedCorrection =
        action === "verify"
          ? await verifyCorrection(targetCorrectionId, { review_notes: reviewNotes })
          : await rejectCorrection(targetCorrectionId, { review_notes: reviewNotes });

      setFeedbackMessage(action === "verify" ? "Correction verified." : "Correction rejected.");
      queryClient.setQueryData<CorrectionRecordResponse>(
        ["correction-detail", targetCorrectionId],
        updatedCorrection
      );
      queryClient.setQueriesData<CorrectionListResponse>(
        { queryKey: ["corrections"] },
        (current) =>
          current
            ? {
                ...current,
                items: current.items.map((item) =>
                  item.id === targetCorrectionId ? updatedCorrection : item
                )
              }
            : current
      );
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
          <section className="min-w-0 space-y-4">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div className="flex items-center gap-3">
                <h2 className="text-2xl font-semibold tracking-tight">Activity feed</h2>
                <Badge variant="outline">{changesQuery.data?.total ?? 0} events</Badge>
              </div>
              <div className="flex gap-3">
                <Button
                  type="button"
                  onClick={() => void handleMarkAllRead()}
                  disabled={isMarkingAllRead || unreadVisibleChangeIds.length === 0}
                >
                  {isMarkingAllRead ? "Marking..." : "Mark All Read"}
                </Button>
              </div>
            </div>
            <Card className="min-w-0" data-testid="changes-activity-card">
              <CardContent className="space-y-4 p-6">
                {changesQuery.error instanceof ApiProblemError ? (
                  <Alert variant="destructive">
                    <AlertTitle>Unable to load changes</AlertTitle>
                    <AlertDescription>{changesQuery.error.problem.detail}</AlertDescription>
                  </Alert>
                ) : changesQuery.isLoading ? (
                  <p className="text-sm text-muted-foreground">Loading change events…</p>
                ) : changesQuery.data && changesQuery.data.items.length > 0 ? (
                  <>
                    <Accordion
                      type="single"
                      collapsible
                      className="space-y-3"
                      data-testid="changes-activity-accordion"
                      value={expandedChangeId}
                      onValueChange={(value) => {
                        setExpandedChangeId(value);
                        if (value) {
                          rememberLoadedChangeId(value);
                          updateParams({ change_id: value, tab: "activity" });
                          return;
                        }
                        updateParams({ change_id: null });
                      }}
                    >
                      {changesQuery.data.items.map((item) => (
                        <ActivityAccordionItem
                          key={item.id}
                          hasLoaded={loadedChangeIds.has(item.id)}
                          isMarkingRead={markingReadId === item.id}
                          isOpen={item.id === expandedChangeId}
                          item={item}
                          onMarkRead={handleMarkRead}
                        />
                      ))}
                    </Accordion>
                    <Pagination
                      currentPage={changePage}
                      totalPages={Math.max(
                        1,
                        Math.ceil(changesQuery.data.total / changesQuery.data.page_size)
                      )}
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
          </section>
        </TabsContent>

        <TabsContent value="corrections">
          <section className="min-w-0 space-y-4">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div className="flex items-center gap-3">
                <h2 className="text-2xl font-semibold tracking-tight">Corrections</h2>
                <Badge variant="outline">{correctionsQuery.data?.total ?? 0} records</Badge>
              </div>
            </div>
            <Card className="min-w-0" data-testid="changes-corrections-card">
              <CardContent className="space-y-4 p-6">
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
                    <Accordion
                      type="single"
                      collapsible
                      className="space-y-3"
                      data-testid="changes-corrections-accordion"
                      value={expandedCorrectionId}
                      onValueChange={(value) => {
                        setExpandedCorrectionId(value);
                        if (value) {
                          rememberLoadedCorrectionId(value);
                          updateParams({ correction_id: value, tab: "corrections" });
                          return;
                        }
                        updateParams({ correction_id: null });
                      }}
                    >
                      {correctionsQuery.data.items.map((item) => (
                        <CorrectionAccordionItem
                          key={item.id}
                          hasLoaded={loadedCorrectionIds.has(item.id)}
                          isOpen={item.id === expandedCorrectionId}
                          isReviewing={
                            reviewAction?.correctionId === item.id ? reviewAction.action : null
                          }
                          item={item}
                          onReview={handleReview}
                          onReviewNotesChange={(value) =>
                            setReviewNotesById((current) => ({
                              ...current,
                              [item.id]: value
                            }))
                          }
                          reviewNotes={reviewNotesById[item.id] ?? ""}
                        />
                      ))}
                    </Accordion>
                    <Pagination
                      currentPage={correctionsPage}
                      totalPages={Math.max(
                        1,
                        Math.ceil(correctionsQuery.data.total / correctionsQuery.data.page_size)
                      )}
                      onPageChange={(nextPage) =>
                        updateParams({ corrections_page: String(nextPage) })
                      }
                    />
                  </>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    No corrections match the current scope and filter.
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

function ActivityAccordionItem({
  hasLoaded,
  isMarkingRead,
  isOpen,
  item,
  onMarkRead
}: {
  hasLoaded: boolean;
  isMarkingRead: boolean;
  isOpen: boolean;
  item: ChangeEventSummary;
  onMarkRead: (changeId: string) => Promise<void>;
}) {
  const detailQuery = useQuery({
    enabled: hasLoaded,
    queryFn: () => readChangeDetail(item.id),
    queryKey: ["change-detail", item.id],
    staleTime: Number.POSITIVE_INFINITY
  });

  return (
    <Card className={isOpen ? "border-primary/40 bg-muted/20" : "shadow-none"}>
      <AccordionItem value={item.id} className="border-none">
        <AccordionTrigger className="px-4 py-4 hover:no-underline">
          <div className="flex min-w-0 flex-1 items-start justify-between gap-4">
            <div className="min-w-0 flex-1 space-y-2 text-left">
              <p className="break-words text-base font-semibold leading-snug">{item.title}</p>
              <p className="break-words text-sm text-muted-foreground">{item.summary}</p>
              <p className="text-sm text-muted-foreground">{formatDateTime(item.created_at)}</p>
            </div>
            <div className="shrink-0">
              <StatusBadge value={item.is_read ? "read" : "unread"} />
            </div>
          </div>
        </AccordionTrigger>
        <AccordionContent className="px-4 pb-4">
          <div
            className="space-y-4 rounded-md border border-border bg-white p-4"
            data-testid={`change-detail-card-${item.id}`}
          >
            <h4 className="text-base font-semibold">Change detail</h4>
            {detailQuery.error instanceof ApiProblemError ? (
              <Alert variant="destructive">
                <AlertTitle>Unable to load change detail</AlertTitle>
                <AlertDescription>{detailQuery.error.problem.detail}</AlertDescription>
              </Alert>
            ) : !hasLoaded ? (
              <p className="text-sm text-muted-foreground">
                Expand this item to load its detail.
              </p>
            ) : detailQuery.isLoading ? (
              <p className="text-sm text-muted-foreground">Loading change detail…</p>
            ) : detailQuery.data ? (
              <>
                <div className="space-y-3">
                  <div className="flex min-w-0 items-start justify-between gap-4">
                    <h5 className="min-w-0 flex-1 break-words text-lg font-semibold">
                      {detailQuery.data.title}
                    </h5>
                    <div className="shrink-0">
                      <StatusBadge value={detailQuery.data.is_read ? "read" : "unread"} />
                    </div>
                  </div>
                  <p className="break-words">{detailQuery.data.summary}</p>
                  <p className="text-sm text-muted-foreground">
                    Event type: {detailQuery.data.event_type} ·{" "}
                    {formatDateTime(detailQuery.data.created_at)}
                  </p>
                  {detailQuery.data.payload ? (
                    <pre className="max-w-full overflow-x-auto rounded-md border bg-slate-950 p-4 text-sm text-slate-100">
                      {JSON.stringify(detailQuery.data.payload, null, 2)}
                    </pre>
                  ) : null}
                </div>
                <div className="flex justify-end">
                  <Button
                    variant="outline"
                    onClick={() => void onMarkRead(item.id)}
                    disabled={isMarkingRead || detailQuery.data.is_read}
                  >
                    {detailQuery.data.is_read
                      ? "Read"
                      : isMarkingRead
                        ? "Marking…"
                        : "Mark read"}
                  </Button>
                </div>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">
                Change detail is unavailable right now.
              </p>
            )}
          </div>
        </AccordionContent>
      </AccordionItem>
    </Card>
  );
}

function CorrectionAccordionItem({
  hasLoaded,
  isOpen,
  isReviewing,
  item,
  onReview,
  onReviewNotesChange,
  reviewNotes
}: {
  hasLoaded: boolean;
  isOpen: boolean;
  isReviewing: "verify" | "reject" | null;
  item: CorrectionRecordResponse;
  onReview: (correctionId: string, action: "verify" | "reject") => Promise<void>;
  onReviewNotesChange: (value: string) => void;
  reviewNotes: string;
}) {
  const detailQuery = useQuery({
    enabled: hasLoaded,
    queryFn: () => readCorrectionDetail(item.id),
    queryKey: ["correction-detail", item.id],
    staleTime: Number.POSITIVE_INFINITY
  });

  return (
    <Card className={isOpen ? "border-primary/40 bg-muted/20" : "shadow-none"}>
      <AccordionItem value={item.id} className="border-none">
        <AccordionTrigger className="px-4 py-4 hover:no-underline">
          <div className="flex min-w-0 flex-1 items-start justify-between gap-4">
            <div className="min-w-0 flex-1 space-y-2 text-left">
              <p className="break-words text-base font-semibold leading-snug">
                {item.proposed_value}
              </p>
              <p className="break-words text-sm text-muted-foreground">
                {item.rationale ?? "No rationale provided"}
              </p>
              <p className="text-sm text-muted-foreground">{formatDateTime(item.created_at)}</p>
            </div>
            <div className="shrink-0">
              <StatusBadge value={item.status} />
            </div>
          </div>
        </AccordionTrigger>
        <AccordionContent className="px-4 pb-4">
          <div
            className="space-y-4 rounded-md border border-border bg-white p-4"
            data-testid={`correction-detail-card-${item.id}`}
          >
            <h4 className="text-base font-semibold">Correction detail</h4>
            {detailQuery.error instanceof ApiProblemError ? (
              <Alert variant="destructive">
                <AlertTitle>Unable to load correction detail</AlertTitle>
                <AlertDescription>{detailQuery.error.problem.detail}</AlertDescription>
              </Alert>
            ) : !hasLoaded ? (
              <p className="text-sm text-muted-foreground">
                Expand this item to load its detail.
              </p>
            ) : detailQuery.isLoading ? (
              <p className="text-sm text-muted-foreground">Loading correction detail…</p>
            ) : detailQuery.data ? (
              <>
                <div className="space-y-3">
                  <div className="flex min-w-0 items-start justify-between gap-4">
                    <h5 className="min-w-0 flex-1 break-words text-lg font-semibold">
                      {detailQuery.data.proposed_value}
                    </h5>
                    <div className="shrink-0">
                      <StatusBadge value={detailQuery.data.status} />
                    </div>
                  </div>
                  <p className="break-words">
                    {detailQuery.data.rationale ?? "No rationale provided."}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    Submitted {formatDateTime(detailQuery.data.created_at)}
                  </p>
                  <p className="break-words text-sm text-muted-foreground">
                    Citation: {formatCitationLabel(detailQuery.data.citation)} ·{" "}
                    {formatSourceTier(detailQuery.data.citation.source_tier)}
                  </p>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium" htmlFor={`review-notes-${item.id}`}>
                    Review notes
                  </label>
                  <Textarea
                    id={`review-notes-${item.id}`}
                    rows={4}
                    value={reviewNotes}
                    onChange={(event) => onReviewNotesChange(event.currentTarget.value)}
                  />
                </div>

                <div className="flex justify-end gap-3">
                  <Button
                    variant="ghost"
                    className="text-destructive hover:text-destructive"
                    onClick={() => void onReview(item.id, "reject")}
                    disabled={isReviewing !== null}
                  >
                    {isReviewing === "reject" ? "Rejecting…" : "Reject"}
                  </Button>
                  <Button
                    onClick={() => void onReview(item.id, "verify")}
                    disabled={isReviewing !== null}
                  >
                    {isReviewing === "verify" ? "Verifying…" : "Verify"}
                  </Button>
                </div>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">
                Correction detail is unavailable right now.
              </p>
            )}
          </div>
        </AccordionContent>
      </AccordionItem>
    </Card>
  );
}
