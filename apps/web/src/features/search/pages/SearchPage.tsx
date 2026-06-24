import type { SearchMode } from "@contracts";
import { useEffect, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { Page, PageHeader } from "@/components/app/page";
import { SelectField } from "@/components/app/select-field";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Pagination } from "@/components/ui/pagination";
import { ApiProblemError } from "@/shared/api/client";
import {
  formatCitationLabel,
  formatScore,
  formatSearchMode,
  formatSourceTier
} from "@/shared/lib/formatting";
import { useSpaceScope } from "@/shared/state/spaceScope";
import { readSearchResults, type SearchQuery } from "../api/searchApi";

const SEARCH_MODE_OPTIONS: Array<{ label: string; value: SearchMode }> = [
  { label: "Combined", value: "combined" },
  { label: "Boolean", value: "boolean" },
  { label: "Vector", value: "vector" },
  { label: "Graph", value: "graph" }
];

const FILE_TYPE_OPTIONS = [
  { label: "PDF", value: "pdf" },
  { label: "DOCX", value: "docx" },
  { label: "Markdown", value: "md" },
  { label: "Text", value: "txt" }
];

export function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { buildReadScopeParams, isReady } = useSpaceScope();
  const [queryText, setQueryText] = useState(searchParams.get("q") ?? "");
  const [documentIdInput, setDocumentIdInput] = useState(searchParams.get("document_id") ?? "");
  const [entityTypeInput, setEntityTypeInput] = useState(searchParams.get("entity_type") ?? "");

  const queryTextParam = searchParams.get("q")?.trim() ?? "";
  const fileTypeParam = searchParams.get("file_type") ?? "";
  const modeParam = (searchParams.get("mode") as SearchMode | null) ?? "combined";
  const documentIdParam = searchParams.get("document_id") ?? "";
  const entityTypeParam = searchParams.get("entity_type") ?? "";
  const page = Math.max(1, Number(searchParams.get("page") ?? "1") || 1);

  useEffect(() => {
    setQueryText(queryTextParam);
    setDocumentIdInput(documentIdParam);
    setEntityTypeInput(entityTypeParam);
  }, [documentIdParam, entityTypeParam, queryTextParam]);

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
        document_id: documentIdInput.trim() || null,
        entity_type: entityTypeInput.trim() || null,
        q: queryText.trim() || null
      },
      true
    );
  }

  const scopeQuery = buildReadScopeParams();
  const searchQuery: SearchQuery = {
    q: queryTextParam || "",
    mode: modeParam,
    page,
    page_size: 10,
    document_id: documentIdParam || undefined,
    entity_type: entityTypeParam || undefined,
    file_type: fileTypeParam || undefined,
    ...scopeQuery
  };

  const resultsQuery = useQuery({
    enabled: isReady && queryTextParam.length > 0,
    queryFn: () => readSearchResults(searchQuery),
    queryKey: ["search-results", searchQuery]
  });

  return (
    <Page>
      <PageHeader
        eyebrow="Retrieval"
        title="Search"
        description="Query the current Space scope across retrieval modes without leaving the workspace."
      />

      <Card>
        <CardContent className="p-6">
          <form className="space-y-5" onSubmit={handleSubmit}>
            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="search-query">
                Search query
              </label>
              <Input
                id="search-query"
                placeholder="Find architecture decisions or implementation details"
                value={queryText}
                onChange={(event) => setQueryText(event.currentTarget.value)}
              />
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <SelectField
                label="Retrieval mode"
                options={SEARCH_MODE_OPTIONS}
                value={modeParam}
                onValueChange={(value) => updateParams({ mode: value }, true)}
              />
              <SelectField
                emptyLabel="All file types"
                label="File type"
                options={FILE_TYPE_OPTIONS}
                placeholder="All file types"
                value={fileTypeParam || null}
                onValueChange={(value) =>
                  updateParams({ file_type: value === "__all__" ? null : value }, true)
                }
              />
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="document-id-filter">
                  Document ID filter
                </label>
                <Input
                  id="document-id-filter"
                  placeholder="Optional document UUID"
                  value={documentIdInput}
                  onChange={(event) => setDocumentIdInput(event.currentTarget.value)}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="entity-type-filter">
                  Entity type filter
                </label>
                <Input
                  id="entity-type-filter"
                  placeholder="Optional entity type"
                  value={entityTypeInput}
                  onChange={(event) => setEntityTypeInput(event.currentTarget.value)}
                />
              </div>
            </div>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-sm text-muted-foreground">
                Empty query state stays idle until you run a search.
              </p>
              <Button type="submit">Run search</Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {!queryTextParam ? (
        <Alert variant="info">
          <AlertTitle>Search is ready</AlertTitle>
          <AlertDescription>
            Enter a query to load retrieval results for the current scope.
          </AlertDescription>
        </Alert>
      ) : resultsQuery.error instanceof ApiProblemError ? (
        <Alert variant="destructive">
          <AlertTitle>Unable to load search results</AlertTitle>
          <AlertDescription>{resultsQuery.error.problem.detail}</AlertDescription>
        </Alert>
      ) : resultsQuery.isLoading ? (
        <p className="text-sm text-muted-foreground">Loading search results…</p>
      ) : resultsQuery.data && resultsQuery.data.items.length > 0 ? (
        <section className="space-y-4">
          <div className="flex items-center justify-between gap-4">
            <h2 className="text-2xl font-semibold tracking-tight">Results</h2>
            <Badge variant="outline">{resultsQuery.data.total} matches</Badge>
          </div>
          <div className="space-y-4">
            {resultsQuery.data.items.map((item) => (
              <Card key={item.result_id}>
                <CardContent className="space-y-5 p-6">
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div className="space-y-1">
                      <h3 className="text-lg font-semibold">
                        {item.document?.title ?? item.entity?.display_name ?? "Retrieval result"}
                      </h3>
                      <p className="text-sm text-muted-foreground">
                        {item.result_kind === "entity"
                          ? item.entity?.entity_type ?? "entity"
                          : item.document?.file_type?.toUpperCase() ?? "document"}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Badge variant="outline">Score {formatScore(item.score)}</Badge>
                      {item.matched_modes?.map((mode) => (
                        <Badge key={mode}>{formatSearchMode(mode)}</Badge>
                      ))}
                    </div>
                  </div>

                  <p className="leading-7 text-foreground">{item.preview_text}</p>

                  {item.citations && item.citations.length > 0 ? (
                    <div className="space-y-2 rounded-md border bg-muted/20 p-4">
                      <p className="text-sm font-semibold">Citations</p>
                      {item.citations.map((citation, index) => (
                        <p key={`${item.result_id}-${index}`} className="text-sm text-muted-foreground">
                          {formatCitationLabel(citation)} · {formatSourceTier(citation.source_tier)}
                        </p>
                      ))}
                    </div>
                  ) : null}

                  <div className="flex flex-wrap gap-3">
                    {item.document?.id ? (
                      <Button asChild variant="outline">
                        <Link to={`/documents/${item.document.id}`}>Open document</Link>
                      </Button>
                    ) : null}
                    {item.entity?.id ? (
                      <Button asChild variant="ghost">
                        <Link to={`/entities/${item.entity.id}`}>Open entity</Link>
                      </Button>
                    ) : null}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
          <Pagination
            currentPage={page}
            totalPages={Math.max(1, Math.ceil(resultsQuery.data.total / resultsQuery.data.page_size))}
            onPageChange={(nextPage) => updateParams({ page: String(nextPage) })}
          />
        </section>
      ) : queryTextParam ? (
        <p className="text-sm text-muted-foreground">
          No results match the current query and scope.
        </p>
      ) : null}
    </Page>
  );
}
