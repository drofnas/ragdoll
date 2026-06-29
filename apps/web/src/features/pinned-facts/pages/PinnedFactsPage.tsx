import type { PinnedFactSummary } from "@contracts";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { Page, PageHeader } from "@/components/app/page";
import { StatusBadge } from "@/components/app/status-badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiProblemError } from "@/shared/api/client";
import { formatDateTime } from "@/shared/lib/formatting";
import { useSpaceScope } from "@/shared/state/spaceScope";
import { listPinnedFacts } from "../api/pinnedFactsApi";

type SortKey = "name" | "status" | "created_by" | "updated_by" | "created_at" | "updated_at";
const PINNED_FACTS_PAGE_SIZE = 100;

function actorLabel(fact: PinnedFactSummary["created_by"] | PinnedFactSummary["updated_by"]) {
  return fact?.full_name?.trim() || fact?.email || "Unknown";
}

function valueLabel(fact: PinnedFactSummary) {
  return fact.value_text ?? JSON.stringify(fact.value_json) ?? "Not set";
}

export function PinnedFactsPage() {
  const { activeSpace, allSpaces, buildReadScopeParams, isReady } = useSpaceScope();
  const readScopeQuery = buildReadScopeParams();
  const writeDisabledReason = allSpaces
    ? "Choose one active Space before creating or editing pinned facts."
    : activeSpace === null
      ? "Choose an active Space before creating or editing pinned facts."
      : null;
  const [sortKey, setSortKey] = useState<SortKey>("name");
  const [descending, setDescending] = useState(false);
  const [nameFilter, setNameFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [createdByFilter, setCreatedByFilter] = useState("");
  const [updatedByFilter, setUpdatedByFilter] = useState("");
  const [createdDateFilter, setCreatedDateFilter] = useState("");
  const [updatedDateFilter, setUpdatedDateFilter] = useState("");

  const listQuery = useMemo(() => ({
    created_by: createdByFilter.trim() || undefined,
    created_date: createdDateFilter.trim() || undefined,
    descending,
    name: nameFilter.trim() || undefined,
    page: 1,
    page_size: PINNED_FACTS_PAGE_SIZE,
    sort_key: sortKey,
    status: statusFilter.trim() || undefined,
    updated_by: updatedByFilter.trim() || undefined,
    updated_date: updatedDateFilter.trim() || undefined,
    ...readScopeQuery
  }), [
    createdByFilter,
    createdDateFilter,
    descending,
    nameFilter,
    readScopeQuery,
    sortKey,
    statusFilter,
    updatedByFilter,
    updatedDateFilter
  ]);

  const factsQuery = useQuery({
    enabled: isReady,
    queryFn: () => listPinnedFacts(listQuery),
    queryKey: ["pinned-facts", listQuery]
  });

  const visibleFacts = factsQuery.data?.items ?? [];

  return (
    <Page>
      <PageHeader
        eyebrow="Evidence-backed memory"
        title="Pinned facts"
        description="Pin the facts that matter, track their evidence, and review changes as new documents arrive."
      />

      {writeDisabledReason ? (
        <Alert variant="info">
          <AlertTitle>Write actions are limited</AlertTitle>
          <AlertDescription>{writeDisabledReason}</AlertDescription>
        </Alert>
      ) : null}

      {factsQuery.error instanceof ApiProblemError ? (
        <Alert variant="destructive">
          <AlertTitle>Unable to load pinned facts</AlertTitle>
          <AlertDescription>{factsQuery.error.problem.detail}</AlertDescription>
        </Alert>
      ) : factsQuery.isLoading ? (
        <p className="text-sm text-muted-foreground">Loading pinned facts…</p>
      ) : (
        <section className="space-y-4">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div className="flex items-center gap-3">
              <h2 className="text-2xl font-semibold tracking-tight">Pinned facts</h2>
              <Badge variant="outline">{visibleFacts.length} visible</Badge>
              <Badge variant="secondary">{factsQuery.data?.total ?? 0} total</Badge>
            </div>
            <div className="flex gap-3">
              <select
                aria-label="Sort pinned facts"
                className="flex h-10 rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={sortKey}
                onChange={(event) => setSortKey(event.currentTarget.value as SortKey)}
              >
                <option value="name">Name</option>
                <option value="status">Status</option>
                <option value="created_by">Created by</option>
                <option value="updated_by">Updated by</option>
                <option value="created_at">Created date</option>
                <option value="updated_at">Updated date</option>
              </select>
              <Button type="button" variant="outline" onClick={() => setDescending((current) => !current)}>
                {descending ? "Reverse: on" : "Reverse: off"}
              </Button>
              {writeDisabledReason ? (
                <Button type="button" disabled>
                  Create Fact
                </Button>
              ) : (
                <Button asChild>
                  <Link to="/pinned-facts/create">Create Fact</Link>
                </Button>
              )}
            </div>
          </div>

          <Card>
            <CardContent className="grid gap-3 p-6 md:grid-cols-2 xl:grid-cols-3">
              <Input
                aria-label="Filter by name"
                placeholder="Filter by name"
                value={nameFilter}
                onChange={(event) => setNameFilter(event.currentTarget.value)}
              />
              <Input
                aria-label="Filter by status"
                placeholder="Filter by status"
                value={statusFilter}
                onChange={(event) => setStatusFilter(event.currentTarget.value)}
              />
              <Input
                aria-label="Filter by created by"
                placeholder="Filter by created by"
                value={createdByFilter}
                onChange={(event) => setCreatedByFilter(event.currentTarget.value)}
              />
              <Input
                aria-label="Filter by updated by"
                placeholder="Filter by updated by"
                value={updatedByFilter}
                onChange={(event) => setUpdatedByFilter(event.currentTarget.value)}
              />
              <Input
                aria-label="Filter by created date"
                placeholder="Filter by created date (YYYY-MM-DD)"
                value={createdDateFilter}
                onChange={(event) => setCreatedDateFilter(event.currentTarget.value)}
              />
              <Input
                aria-label="Filter by updated date"
                placeholder="Filter by updated date (YYYY-MM-DD)"
                value={updatedDateFilter}
                onChange={(event) => setUpdatedDateFilter(event.currentTarget.value)}
              />
            </CardContent>
          </Card>

          {visibleFacts.length ? (
            visibleFacts.map((fact) => (
              <Card key={fact.id}>
                <CardContent className="space-y-4 p-6">
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div className="space-y-1">
                      <h3 className="text-lg font-semibold">{fact.title}</h3>
                      <p className="text-sm text-muted-foreground">{fact.description}</p>
                      <p className="text-xs text-muted-foreground">{fact.key}</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <StatusBadge value={fact.status} />
                      {fact.pending_candidate_count > 0 ? (
                        <Badge variant="secondary">{fact.pending_candidate_count} pending</Badge>
                      ) : null}
                      {fact.status === "missing_evidence" ? <Badge variant="destructive">Missing evidence</Badge> : null}
                      {fact.is_active ? <Badge variant="outline">Active</Badge> : <Badge variant="secondary">Inactive</Badge>}
                    </div>
                  </div>

                  {(fact.status === "pending_update" || fact.status === "conflicted" || fact.status === "missing_evidence") && (
                    <Alert variant={fact.status === "missing_evidence" ? "destructive" : "info"}>
                      <AlertTitle>
                        {fact.status === "pending_update"
                          ? "Pending update"
                          : fact.status === "conflicted"
                            ? "Conflicting updates"
                            : "Evidence missing"}
                      </AlertTitle>
                      <AlertDescription>
                        {fact.status === "pending_update"
                          ? "The stored value stays live until you review and accept a proposed update."
                          : fact.status === "conflicted"
                            ? "Multiple proposed values were detected. Review the candidates before changing the stored value."
                            : "The current stored value is still shown, but the latest rerun did not find supporting evidence."}
                      </AlertDescription>
                    </Alert>
                  )}

                  <div className="grid gap-4 md:grid-cols-3">
                    <Card className="bg-background/65 shadow-none">
                      <CardContent className="space-y-2 p-4">
                        <p className="text-sm font-semibold">Current value</p>
                        <p className="text-sm">{valueLabel(fact)}</p>
                      </CardContent>
                    </Card>
                    <Card className="bg-background/65 shadow-none">
                      <CardContent className="space-y-2 p-4">
                        <p className="text-sm font-semibold">Created / updated</p>
                        <p className="text-sm">{actorLabel(fact.created_by)}</p>
                        <p className="text-xs text-muted-foreground">{formatDateTime(fact.created_at)}</p>
                        <p className="text-sm">{actorLabel(fact.updated_by)}</p>
                        <p className="text-xs text-muted-foreground">{formatDateTime(fact.updated_at)}</p>
                      </CardContent>
                    </Card>
                    <Card className="bg-background/65 shadow-none">
                      <CardContent className="space-y-2 p-4">
                        <p className="text-sm font-semibold">Last checked</p>
                        <p className="text-sm">{formatDateTime(fact.last_checked_at)}</p>
                      </CardContent>
                    </Card>
                  </div>
                  <div className="flex justify-end">
                    <Button asChild variant="outline">
                      <Link to={`/pinned-facts/${fact.id}`}>Open detail</Link>
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))
          ) : (
            <p className="text-sm text-muted-foreground">
              No pinned facts match the current filters.
            </p>
          )}
        </section>
      )}
    </Page>
  );
}
