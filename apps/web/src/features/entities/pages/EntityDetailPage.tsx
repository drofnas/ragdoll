import { useQuery } from "@tanstack/react-query";
import { Link, Navigate, useParams, useSearchParams } from "react-router-dom";

import { Page, PageHeader } from "@/components/app/page";
import { SelectField } from "@/components/app/select-field";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiProblemError } from "@/shared/api/client";
import {
  formatCitationLabel,
  formatDateTime,
  formatSourceTier
} from "@/shared/lib/formatting";
import { useSpaceScope } from "@/shared/state/spaceScope";
import { readEntity, readEntitySubgraph } from "../api/entitiesApi";

const DEPTH_OPTIONS = [
  { label: "1 hop", value: "1" },
  { label: "2 hops", value: "2" },
  { label: "3 hops", value: "3" }
];

const LIMIT_OPTIONS = [
  { label: "10 links", value: "10" },
  { label: "25 links", value: "25" },
  { label: "50 links", value: "50" }
];

export function EntityDetailPage() {
  const { entityId } = useParams<{ entityId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const { buildReadScopeParams, isReady } = useSpaceScope();

  const depth = Math.max(1, Number(searchParams.get("depth") ?? "1") || 1);
  const limit = Math.max(1, Number(searchParams.get("limit") ?? "25") || 25);
  const scopeQuery = buildReadScopeParams();

  if (!entityId) {
    return <Navigate to="/entities" replace />;
  }

  const detailQuery = useQuery({
    enabled: isReady,
    queryFn: () => readEntity(entityId, scopeQuery),
    queryKey: ["entity-detail", entityId, scopeQuery]
  });

  const graphQuery = useQuery({
    enabled: isReady,
    queryFn: () =>
      readEntitySubgraph(entityId, {
        depth,
        limit,
        ...scopeQuery
      }),
    queryKey: ["entity-graph", entityId, depth, limit, scopeQuery]
  });

  function updateGraphParams(next: Record<string, string>) {
    const params = new URLSearchParams(searchParams);
    for (const [key, value] of Object.entries(next)) {
      params.set(key, value);
    }
    setSearchParams(params);
  }

  const fallbackNode = graphQuery.data?.nodes?.[0];

  return (
    <Page>
      <PageHeader
        eyebrow="Entity detail"
        title={detailQuery.data?.display_name ?? fallbackNode?.label ?? "Entity detail"}
        description={detailQuery.data?.entity_type ?? fallbackNode?.node_type ?? "Loading entity metadata"}
        actions={detailQuery.data ? <Badge variant="outline">{detailQuery.data.document_count} documents</Badge> : undefined}
      >
        <div>
          <Button asChild variant="ghost">
            <Link to="/entities">Back to entities</Link>
          </Button>
        </div>
      </PageHeader>

      {detailQuery.error instanceof ApiProblemError ? (
        <Alert variant="destructive">
          <AlertTitle>Unable to load the selected entity</AlertTitle>
          <AlertDescription>{detailQuery.error.problem.detail}</AlertDescription>
        </Alert>
      ) : detailQuery.isLoading ? (
        <p className="text-sm text-muted-foreground">Loading entity detail…</p>
      ) : detailQuery.data ? (
        <>
          <section className="grid gap-4 lg:grid-cols-3">
            <Card>
              <CardHeader>
                <CardTitle>Overview</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <p>Normalized name: {detailQuery.data.normalized_name}</p>
                <p>Mentions: {detailQuery.data.mention_count}</p>
                <p>Latest mention: {formatDateTime(detailQuery.data.latest_mentioned_at)}</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Graph controls</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <SelectField
                  label="Depth"
                  options={DEPTH_OPTIONS}
                  value={String(depth)}
                  onValueChange={(value) => updateGraphParams({ depth: value })}
                />
                <SelectField
                  label="Limit"
                  options={LIMIT_OPTIONS}
                  value={String(limit)}
                  onValueChange={(value) => updateGraphParams({ limit: value })}
                />
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Related docs</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <p>{detailQuery.data.related_documents?.length ?? 0} linked documents</p>
                <p>{graphQuery.data?.links?.length ?? 0} graph links loaded</p>
              </CardContent>
            </Card>
          </section>

          <section className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Provenance</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {detailQuery.data.provenance && detailQuery.data.provenance.length > 0 ? (
                  detailQuery.data.provenance.map((mention) => (
                    <Card key={mention.mention_id} className="bg-background/65 shadow-none">
                      <CardContent className="space-y-2 p-5">
                        <p className="font-semibold">{mention.surface_text}</p>
                        <p className="text-sm text-muted-foreground">
                          {formatCitationLabel(mention.citation)} ·{" "}
                          {formatSourceTier(mention.citation.source_tier)}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          Mentioned {formatDateTime(mention.created_at)}
                        </p>
                      </CardContent>
                    </Card>
                  ))
                ) : (
                  <p className="text-sm text-muted-foreground">
                    No provenance records are available yet.
                  </p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Mention history</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {detailQuery.data.history && detailQuery.data.history.length > 0 ? (
                  detailQuery.data.history.map((entry) => (
                    <Card key={entry.mention_id} className="bg-background/65 shadow-none">
                      <CardContent className="space-y-2 p-5">
                        <p className="font-semibold">{entry.surface_text}</p>
                        <p className="text-sm text-muted-foreground">
                          {formatCitationLabel(entry.citation)} · observed{" "}
                          {formatDateTime(entry.observed_at)}
                        </p>
                      </CardContent>
                    </Card>
                  ))
                ) : (
                  <p className="text-sm text-muted-foreground">
                    No chronological mention history is available yet.
                  </p>
                )}
              </CardContent>
            </Card>
          </section>

          <section className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Related documents</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {detailQuery.data.related_documents &&
                detailQuery.data.related_documents.length > 0 ? (
                  detailQuery.data.related_documents.map((document) => (
                    <div
                      key={document.document_id}
                      className="flex flex-col gap-2 rounded-md border bg-muted/20 p-4 sm:flex-row sm:items-start sm:justify-between"
                    >
                      <div className="space-y-2">
                        <Button asChild variant="ghost" className="h-auto px-0 py-0">
                          <Link to={`/documents/${document.document_id}`}>{document.title}</Link>
                        </Button>
                        <p className="text-sm text-muted-foreground">
                          {document.file_type.toUpperCase()} · {document.mention_count} mentions
                        </p>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        {formatDateTime(document.latest_mentioned_at)}
                      </p>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-muted-foreground">
                    No related documents are linked yet.
                  </p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Lightweight graph view</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {graphQuery.error instanceof ApiProblemError ? (
                  <Alert variant="destructive">
                    <AlertTitle>Unable to load graph links</AlertTitle>
                    <AlertDescription>{graphQuery.error.problem.detail}</AlertDescription>
                  </Alert>
                ) : graphQuery.isLoading ? (
                  <p className="text-sm text-muted-foreground">Loading graph relationships…</p>
                ) : graphQuery.data ? (
                  <>
                    <div className="space-y-2">
                      <p className="text-sm font-semibold">Nodes</p>
                      {graphQuery.data.nodes && graphQuery.data.nodes.length > 0 ? (
                        graphQuery.data.nodes.map((node) => (
                          <p key={node.id} className="text-sm text-muted-foreground">
                            {node.label} · {node.node_type}
                          </p>
                        ))
                      ) : (
                        <p className="text-sm text-muted-foreground">
                          No nodes were returned for this depth and limit.
                        </p>
                      )}
                    </div>
                    <div className="space-y-2">
                      <p className="text-sm font-semibold">Links</p>
                      {graphQuery.data.links && graphQuery.data.links.length > 0 ? (
                        graphQuery.data.links.map((link, index) => (
                          <p
                            key={`${link.source_id}-${link.target_id}-${index}`}
                            className="text-sm text-muted-foreground"
                          >
                            {link.source_id} → {link.target_id} · {link.relation_type}
                          </p>
                        ))
                      ) : (
                        <p className="text-sm text-muted-foreground">
                          No relationship links were returned for this entity.
                        </p>
                      )}
                    </div>
                  </>
                ) : null}
              </CardContent>
            </Card>
          </section>
        </>
      ) : null}
    </Page>
  );
}
