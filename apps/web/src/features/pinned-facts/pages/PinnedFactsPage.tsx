import type { SearchResult } from "@contracts";
import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
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
import { readSearchResults } from "../../search/api/searchApi";
import { createPinnedFact, listPinnedFacts } from "../api/pinnedFactsApi";

export function PinnedFactsPage() {
  const { activeSpace, allSpaces, buildReadScopeParams, isReady } = useSpaceScope();
  const readScopeQuery = buildReadScopeParams();
  const writeScopeQuery = !allSpaces && activeSpace ? { space_id: activeSpace.id } : null;
  const writeDisabledReason = allSpaces
    ? "Choose one active Space before creating or editing pinned facts."
    : activeSpace === null
      ? "Choose an active Space before creating or editing pinned facts."
      : null;

  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [key, setKey] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [entityTypeHint, setEntityTypeHint] = useState("");
  const [valueKind, setValueKind] = useState<"json" | "text">("text");
  const [valueInput, setValueInput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [submittedSearchQuery, setSubmittedSearchQuery] = useState("");
  const [selectedResultId, setSelectedResultId] = useState<string | null>(null);

  const factsQuery = useQuery({
    enabled: isReady,
    queryFn: () => listPinnedFacts({ page: 1, page_size: 50, ...readScopeQuery }),
    queryKey: ["pinned-facts", readScopeQuery]
  });

  const evidenceQuery = useQuery({
    enabled: isReady && submittedSearchQuery.trim().length > 0,
    queryFn: () =>
      readSearchResults({
        mode: "combined",
        page: 1,
        page_size: 5,
        q: submittedSearchQuery,
        ...readScopeQuery
      }),
    queryKey: ["pinned-facts-evidence-search", submittedSearchQuery, readScopeQuery]
  });

  const selectedResult =
    evidenceQuery.data?.items.find((item) => item.result_id === selectedResultId) ?? null;

  function submitEvidenceSearch() {
    setSubmittedSearchQuery(searchQuery.trim());
    setSelectedResultId(null);
  }

  async function handleCreateFact(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!writeScopeQuery) {
      setErrorMessage(writeDisabledReason);
      return;
    }
    if (!selectedResult) {
      setErrorMessage("Choose one search result as supporting evidence before creating the fact.");
      return;
    }

    setErrorMessage(null);
    setFeedbackMessage(null);
    setIsCreating(true);

    try {
      const payload =
        valueKind === "json"
          ? {
              value_json: JSON.parse(valueInput) as Record<string, unknown>,
              value_kind: "json" as const,
              value_text: null
            }
          : {
              value_json: null,
              value_kind: "text" as const,
              value_text: valueInput
            };

      await createPinnedFact(
        {
          confidence: 0.95,
          description,
          entity_type_hint: entityTypeHint || null,
          evidence: [
            {
              citations: selectedResult.citations,
              quote: selectedResult.preview_text,
              source_chunk_ids: selectedResult.citations
                .map((citation) => citation.chunk_id)
                .filter((value): value is string => Boolean(value))
            }
          ],
          is_active: true,
          key,
          source_document_id: selectedResult.document?.id ?? selectedResult.citations[0]?.document_id ?? null,
          title,
          ...payload
        },
        writeScopeQuery
      );
      setFeedbackMessage("Pinned fact created.");
      setKey("");
      setTitle("");
      setDescription("");
      setEntityTypeHint("");
      setValueInput("");
      await factsQuery.refetch();
    } catch (error) {
      if (error instanceof SyntaxError) {
        setErrorMessage("JSON values must be valid JSON before the fact can be created.");
      } else if (error instanceof ApiProblemError) {
        setErrorMessage(error.problem.detail);
      } else {
        setErrorMessage("Unable to create that pinned fact right now.");
      }
    } finally {
      setIsCreating(false);
    }
  }

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

      <Card>
        <CardHeader>
          <CardTitle>Create pinned fact</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <form className="space-y-5" onSubmit={handleCreateFact}>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="pinned-fact-key">
                  Key
                </label>
                <Input
                  id="pinned-fact-key"
                  required
                  disabled={!writeScopeQuery || isCreating}
                  placeholder="project_color_scheme"
                  value={key}
                  onChange={(event) => setKey(event.currentTarget.value)}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="pinned-fact-title">
                  Title
                </label>
                <Input
                  id="pinned-fact-title"
                  required
                  disabled={!writeScopeQuery || isCreating}
                  placeholder="Project color scheme"
                  value={title}
                  onChange={(event) => setTitle(event.currentTarget.value)}
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="pinned-fact-description">
                Description / detection query
              </label>
              <Textarea
                id="pinned-fact-description"
                required
                disabled={!writeScopeQuery || isCreating}
                rows={3}
                placeholder="What is the current project color scheme?"
                value={description}
                onChange={(event) => setDescription(event.currentTarget.value)}
              />
            </div>

            <div className="grid gap-4 md:grid-cols-[minmax(0,160px)_1fr]">
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="pinned-fact-value-kind">
                  Value type
                </label>
                <Input
                  id="pinned-fact-value-kind"
                  disabled
                  value={valueKind}
                  onFocus={() => undefined}
                />
                <div className="flex gap-2">
                  <Button type="button" variant={valueKind === "text" ? "default" : "outline"} onClick={() => setValueKind("text")}>
                    Text
                  </Button>
                  <Button type="button" variant={valueKind === "json" ? "default" : "outline"} onClick={() => setValueKind("json")}>
                    JSON
                  </Button>
                </div>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="pinned-fact-value">
                  Current value
                </label>
                <Textarea
                  id="pinned-fact-value"
                  required
                  disabled={!writeScopeQuery || isCreating}
                  rows={4}
                  placeholder={valueKind === "json" ? '{ "primary": "#2563eb" }' : "Atlas"}
                  value={valueInput}
                  onChange={(event) => setValueInput(event.currentTarget.value)}
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="pinned-fact-entity-type">
                Entity type hint
              </label>
              <Input
                id="pinned-fact-entity-type"
                disabled={!writeScopeQuery || isCreating}
                placeholder="Optional entity type"
                value={entityTypeHint}
                onChange={(event) => setEntityTypeHint(event.currentTarget.value)}
              />
            </div>

            <Card className="bg-background/70 shadow-none">
              <CardHeader>
                <CardTitle className="text-base">Select supporting evidence</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex gap-3">
                  <Input
                    placeholder="Search for the source evidence you want to pin"
                    value={searchQuery}
                    onChange={(event) => setSearchQuery(event.currentTarget.value)}
                  />
                  <Button type="button" onClick={submitEvidenceSearch}>
                    Search
                  </Button>
                </div>

                {evidenceQuery.error instanceof ApiProblemError ? (
                  <Alert variant="destructive">
                    <AlertTitle>Unable to search evidence</AlertTitle>
                    <AlertDescription>{evidenceQuery.error.problem.detail}</AlertDescription>
                  </Alert>
                ) : evidenceQuery.isLoading ? (
                  <p className="text-sm text-muted-foreground">Searching evidence…</p>
                ) : evidenceQuery.data?.items.length ? (
                  <div className="space-y-3">
                    {evidenceQuery.data.items.map((item) => (
                      <Card
                        key={item.result_id}
                        className={selectedResultId === item.result_id ? "border-primary" : ""}
                      >
                        <CardContent className="space-y-3 p-4">
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <p className="font-medium">
                                {item.document?.title ?? item.entity?.display_name ?? "Result"}
                              </p>
                              <p className="text-sm text-muted-foreground">{item.preview_text}</p>
                            </div>
                            <Button type="button" variant={selectedResultId === item.result_id ? "default" : "outline"} onClick={() => setSelectedResultId(item.result_id)}>
                              {selectedResultId === item.result_id ? "Selected" : "Use result"}
                            </Button>
                          </div>
                          {item.citations.map((citation, index) => (
                            <p key={`${item.result_id}-${index}`} className="text-sm text-muted-foreground">
                              {formatCitationLabel(citation)}
                            </p>
                          ))}
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                ) : submittedSearchQuery ? (
                  <p className="text-sm text-muted-foreground">No evidence matched that search yet.</p>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    Run a search and select one result to attach evidence to the fact.
                  </p>
                )}
              </CardContent>
            </Card>

            <div className="flex justify-end">
              <Button disabled={!writeScopeQuery || !selectedResult} type="submit">
                {isCreating ? "Creating…" : "Create pinned fact"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {factsQuery.error instanceof ApiProblemError ? (
        <Alert variant="destructive">
          <AlertTitle>Unable to load pinned facts</AlertTitle>
          <AlertDescription>{factsQuery.error.problem.detail}</AlertDescription>
        </Alert>
      ) : factsQuery.isLoading ? (
        <p className="text-sm text-muted-foreground">Loading pinned facts…</p>
      ) : (
        <section className="space-y-4">
          <div className="flex items-center justify-between gap-4">
            <h2 className="text-2xl font-semibold tracking-tight">Pinned facts</h2>
            <Badge variant="outline">{factsQuery.data?.total ?? 0} facts</Badge>
          </div>
          {factsQuery.data?.items.length ? (
            factsQuery.data.items.map((fact) => (
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
                      {fact.is_active ? <Badge variant="outline">Active</Badge> : <Badge variant="secondary">Inactive</Badge>}
                    </div>
                  </div>
                  <div className="grid gap-4 md:grid-cols-3">
                    <Card className="bg-background/65 shadow-none">
                      <CardContent className="space-y-2 p-4">
                        <p className="text-sm font-semibold">Current value</p>
                        <p className="text-sm">{fact.value_text ?? JSON.stringify(fact.value_json) ?? "Not set"}</p>
                      </CardContent>
                    </Card>
                    <Card className="bg-background/65 shadow-none">
                      <CardContent className="space-y-2 p-4">
                        <p className="text-sm font-semibold">Pending review</p>
                        <p className="text-sm">{fact.pending_candidate_count} candidates</p>
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
              No pinned facts are configured for this scope yet.
            </p>
          )}
        </section>
      )}
    </Page>
  );
}
