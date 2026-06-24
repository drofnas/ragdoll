import { useEffect, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { Page, PageHeader } from "@/components/app/page";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Pagination } from "@/components/ui/pagination";
import { ApiProblemError } from "@/shared/api/client";
import { formatDateTime } from "@/shared/lib/formatting";
import { useSpaceScope } from "@/shared/state/spaceScope";
import { listEntities, type ListEntitiesQuery } from "../api/entitiesApi";

export function EntitiesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { buildReadScopeParams, isReady } = useSpaceScope();
  const [queryText, setQueryText] = useState(searchParams.get("q") ?? "");
  const [entityTypeText, setEntityTypeText] = useState(searchParams.get("entity_type") ?? "");

  const queryTextParam = searchParams.get("q") ?? "";
  const entityTypeParam = searchParams.get("entity_type") ?? "";
  const page = Math.max(1, Number(searchParams.get("page") ?? "1") || 1);

  useEffect(() => {
    setQueryText(queryTextParam);
    setEntityTypeText(entityTypeParam);
  }, [entityTypeParam, queryTextParam]);

  function updateParams(updates: Record<string, string | null | undefined>, resetPage = false) {
    const next = new URLSearchParams(searchParams);
    for (const [key, value] of Object.entries(updates)) {
      if (!value) {
        next.delete(key);
      } else {
        next.set(key, value);
      }
    }
    if (resetPage) {
      next.delete("page");
    }
    setSearchParams(next);
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    updateParams(
      {
        entity_type: entityTypeText.trim() || null,
        q: queryText.trim() || null
      },
      true
    );
  }

  const scopeQuery = buildReadScopeParams();
  const entityQuery: ListEntitiesQuery = {
    page,
    page_size: 12,
    q: queryTextParam || undefined,
    entity_type: entityTypeParam || undefined,
    ...scopeQuery
  };

  const entitiesQuery = useQuery({
    enabled: isReady,
    queryFn: () => listEntities(entityQuery),
    queryKey: ["entities", entityQuery]
  });

  return (
    <Page>
      <PageHeader
        eyebrow="Knowledge graph"
        title="Entities"
        description="Explore extracted entities, their provenance, and how often they appear in the current scope."
      />

      <Card>
        <CardContent className="p-6">
          <form className="space-y-5" onSubmit={handleSubmit}>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="entity-search">
                  Search entities
                </label>
                <Input
                  id="entity-search"
                  placeholder="Find a person, system, or concept"
                  value={queryText}
                  onChange={(event) => setQueryText(event.currentTarget.value)}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="entity-type">
                  Entity type
                </label>
                <Input
                  id="entity-type"
                  placeholder="Optional entity type"
                  value={entityTypeText}
                  onChange={(event) => setEntityTypeText(event.currentTarget.value)}
                />
              </div>
            </div>
            <div className="flex justify-end">
              <Button type="submit">Apply filters</Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {entitiesQuery.error instanceof ApiProblemError ? (
        <Alert variant="destructive">
          <AlertTitle>Unable to load entities</AlertTitle>
          <AlertDescription>{entitiesQuery.error.problem.detail}</AlertDescription>
        </Alert>
      ) : entitiesQuery.isLoading ? (
        <p className="text-sm text-muted-foreground">Loading entities…</p>
      ) : entitiesQuery.data && entitiesQuery.data.items.length > 0 ? (
        <section className="space-y-4">
          <div className="flex items-center justify-between gap-4">
            <h2 className="text-2xl font-semibold tracking-tight">Results</h2>
            <Badge variant="outline">{entitiesQuery.data.total} entities</Badge>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            {entitiesQuery.data.items.map((entity) => (
              <Card key={entity.id}>
                <CardContent className="space-y-5 p-6">
                  <div className="flex items-start justify-between gap-4">
                    <div className="space-y-1">
                      <h3 className="text-lg font-semibold">{entity.display_name}</h3>
                      <p className="text-sm text-muted-foreground">{entity.entity_type}</p>
                    </div>
                    <Badge variant="outline">{entity.document_count} documents</Badge>
                  </div>

                  <p className="text-sm text-muted-foreground">
                    {entity.mention_count} mentions · latest mention{" "}
                    {formatDateTime(entity.latest_mentioned_at)}
                  </p>

                  <Button asChild variant="outline">
                    <Link to={`/entities/${entity.id}`}>Open entity detail</Link>
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
          <Pagination
            currentPage={page}
            totalPages={Math.max(1, Math.ceil(entitiesQuery.data.total / entitiesQuery.data.page_size))}
            onPageChange={(nextPage) => updateParams({ page: String(nextPage) })}
          />
        </section>
      ) : (
        <p className="text-sm text-muted-foreground">
          No entities match the current scope and filters.
        </p>
      )}
    </Page>
  );
}
