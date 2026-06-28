import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { Page, PageHeader } from "@/components/app/page";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiProblemError } from "@/shared/api/client";
import { formatDateTime } from "@/shared/lib/formatting";
import { useSpaceScope } from "@/shared/state/spaceScope";
import { readUsageSummary } from "../../account/api/accountApi";
import { listDocuments } from "../../documents/api/documentsApi";
import { listPinnedFacts } from "../../pinned-facts/api/pinnedFactsApi";

export function DashboardPage() {
  const { buildReadScopeParams, isReady } = useSpaceScope();
  const scopeQuery = buildReadScopeParams();

  const documentsQuery = useQuery({
    enabled: isReady,
    queryFn: () =>
      listDocuments({
        page: 1,
        page_size: 5,
        ...scopeQuery
      }),
    queryKey: ["dashboard-documents", scopeQuery]
  });

  const usageQuery = useQuery({
    queryFn: readUsageSummary,
    queryKey: ["dashboard-usage"]
  });
  const pinnedFactsQuery = useQuery({
    enabled: isReady,
    queryFn: () =>
      listPinnedFacts({
        descending: true,
        page: 1,
        page_size: 5,
        sort_key: "updated_at",
        ...scopeQuery
      }),
    queryKey: ["dashboard-pinned-facts", scopeQuery]
  });
  const recentPinnedFacts = pinnedFactsQuery.data?.items ?? [];

  return (
    <Page>
      <PageHeader
        eyebrow="Overview"
        title="Workspace dashboard"
        description="Use the shell scope controls to change what this dashboard summarizes."
      />

      <section className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle>Documents in scope</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-4xl font-semibold tracking-tight">
              {documentsQuery.data?.total ?? 0}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardTitle>Configured retrieval budget</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-4xl font-semibold tracking-tight">
              {usageQuery.data?.limits.retrieval_chunks ?? "…"}
            </p>
            <p className="text-sm text-muted-foreground">
              Chunks available to retrieval-backed features
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardTitle>Upload status</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-4xl font-semibold tracking-tight">
              {usageQuery.data?.status.partially_indexed_documents ?? 0}
            </p>
            <p className="text-sm text-muted-foreground">
              Documents still working through processing
            </p>
          </CardContent>
        </Card>
      </section>

      {documentsQuery.error instanceof ApiProblemError ? (
        <Alert variant="destructive">
          <AlertTitle>Unable to load recent documents</AlertTitle>
          <AlertDescription>{documentsQuery.error.problem.detail}</AlertDescription>
        </Alert>
      ) : null}

      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-4 space-y-0">
          <div className="space-y-2">
            <CardTitle>Recent documents</CardTitle>
            <p className="text-sm text-muted-foreground">
              The most recently updated documents inside the current read scope.
            </p>
          </div>
          <Button asChild variant="outline">
            <Link to="/documents">Open library</Link>
          </Button>
        </CardHeader>
        <CardContent>
          {documentsQuery.isLoading ? (
            <p className="text-sm text-muted-foreground">Loading recent documents…</p>
          ) : documentsQuery.data && documentsQuery.data.items.length > 0 ? (
            <div className="space-y-3">
              {documentsQuery.data.items.map((document) => (
                <div
                  key={document.id}
                  className="flex flex-col gap-2 rounded-md border bg-muted/20 p-4 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="space-y-1">
                    <p className="font-semibold text-foreground">{document.title}</p>
                    <p className="text-sm text-muted-foreground">
                      {document.original_filename}
                    </p>
                  </div>
                  <div className="space-y-1 text-left sm:text-right">
                    <p className="text-sm font-medium text-foreground">
                      {document.processing_status.overall}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {formatDateTime(document.updated_at)}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              Upload a document to start filling in the dashboard.
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-4 space-y-0">
          <div className="space-y-2">
            <CardTitle>Pinned facts</CardTitle>
            <p className="text-sm text-muted-foreground">
              The most recently updated pinned facts inside the current read scope.
            </p>
          </div>
          <Button asChild variant="outline">
            <Link to="/pinned-facts">Open pinned facts</Link>
          </Button>
        </CardHeader>
        <CardContent>
          {pinnedFactsQuery.isLoading ? (
            <p className="text-sm text-muted-foreground">Loading pinned facts…</p>
          ) : recentPinnedFacts.length > 0 ? (
            <div className="space-y-3">
              {recentPinnedFacts.map((fact) => (
                <div
                  key={fact.id}
                  className="flex flex-col gap-2 rounded-md border bg-muted/20 p-4 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="space-y-1">
                    <p className="font-semibold text-foreground">{fact.title}</p>
                    <p className="text-sm text-muted-foreground">{fact.value_text ?? JSON.stringify(fact.value_json)}</p>
                  </div>
                  <div className="space-y-1 text-left sm:text-right">
                    <p className="text-sm font-medium text-foreground">{fact.status}</p>
                    <p className="text-xs text-muted-foreground">{formatDateTime(fact.updated_at)}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              Create a pinned fact to track evidence-backed values here.
            </p>
          )}
        </CardContent>
      </Card>
    </Page>
  );
}
