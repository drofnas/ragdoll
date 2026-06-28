import type { SearchResult } from "@contracts";
import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { Page, PageHeader } from "@/components/app/page";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ApiProblemError } from "@/shared/api/client";
import {
  formatCitationLabel,
  formatScore,
  formatSearchMode,
  formatSourceTier
} from "@/shared/lib/formatting";
import { useSpaceScope } from "@/shared/state/spaceScope";
import { readSearchResults } from "../../search/api/searchApi";
import type { PinnedFactEvidencePayload } from "../api/pinnedFactsApi";
import { createPinnedFact } from "../api/pinnedFactsApi";

type CreatePageLocationState = {
  draft?: {
    description: string;
    evidence: PinnedFactEvidencePayload[];
    origin_label?: string | null;
    source_document_id?: string | null;
    title?: string | null;
    value_json?: Record<string, unknown> | null;
    value_kind: "json" | "text";
    value_text?: string | null;
  };
};

function buildEvidencePayload(result: SearchResult): PinnedFactEvidencePayload | null {
  const quote = result.preview_text.trim();
  if (!quote) {
    return null;
  }
  return {
    citations: result.citations,
    quote,
    source_chunk_ids: result.citations
      .map((citation) => citation.chunk_id)
      .filter((value): value is string => Boolean(value))
  };
}

function buildSourceDocumentId(result: SearchResult) {
  return result.document?.id ?? result.citations[0]?.document_id ?? null;
}

function formatInitialValueInput(locationState: CreatePageLocationState["draft"] | undefined) {
  if (!locationState) {
    return "";
  }
  if (locationState.value_kind === "json") {
    return JSON.stringify(locationState.value_json ?? {}, null, 2);
  }
  return locationState.value_text ?? "";
}

export function PinnedFactCreatePage() {
  const navigate = useNavigate();
  const location = useLocation();
  const locationState = (location.state as CreatePageLocationState | null)?.draft;
  const { activeSpace, allSpaces, buildReadScopeParams, isReady } = useSpaceScope();
  const readScopeQuery = buildReadScopeParams();
  const writeScopeQuery = !allSpaces && activeSpace ? { space_id: activeSpace.id } : null;
  const writeDisabledReason = allSpaces
    ? "Choose one active Space before creating or editing pinned facts."
    : activeSpace === null
      ? "Choose an active Space before creating or editing pinned facts."
      : null;

  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [isTestingQuery, setIsTestingQuery] = useState(false);
  const [key, setKey] = useState("");
  const [title, setTitle] = useState(locationState?.title ?? "");
  const [description, setDescription] = useState(locationState?.description ?? "");
  const [entityTypeHint] = useState("");
  const [valueKind, setValueKind] = useState<"json" | "text">(locationState?.value_kind ?? "text");
  const [valueInput, setValueInput] = useState(formatInitialValueInput(locationState));
  const [testedQuery, setTestedQuery] = useState("");
  const [testedEntityTypeHint, setTestedEntityTypeHint] = useState("");
  const [testResults, setTestResults] = useState<SearchResult[]>([]);
  const [testResultCount, setTestResultCount] = useState<number | null>(null);

  const trimmedKey = key.trim();
  const trimmedTitle = title.trim();
  const trimmedDescription = description.trim();
  const trimmedEntityTypeHint = entityTypeHint.trim();
  const hasTestedQuery = testedQuery.length > 0 || testedEntityTypeHint.length > 0;
  const hasCurrentTestResults =
    hasTestedQuery &&
    testedQuery === trimmedDescription &&
    testedEntityTypeHint === trimmedEntityTypeHint;
  const primaryResult = hasCurrentTestResults ? testResults[0] ?? null : null;
  const seededEvidence = locationState?.evidence ?? [];
  const canUseSeededEvidence = seededEvidence.length > 0 && !hasCurrentTestResults;
  const isFormValid =
    trimmedKey.length > 0 &&
    trimmedTitle.length > 0 &&
    trimmedDescription.length > 0 &&
    valueInput.trim().length > 0;
  const canCreate = Boolean(
    writeScopeQuery &&
      isFormValid &&
      !isCreating &&
      (testResults.length > 0 && hasCurrentTestResults ? primaryResult : canUseSeededEvidence)
  );
  const shouldRefreshTestResults =
    (testedQuery.length > 0 || testedEntityTypeHint.length > 0) && !hasCurrentTestResults;

  async function handleTestQuery() {
    if (!trimmedDescription) {
      setErrorMessage("Enter a detection query before testing it.");
      return;
    }

    setErrorMessage(null);
    setIsTestingQuery(true);

    try {
      const response = await readSearchResults({
        mode: "combined",
        page: 1,
        page_size: 5,
        q: trimmedDescription,
        entity_type: trimmedEntityTypeHint || undefined,
        ...readScopeQuery
      });
      setTestedQuery(trimmedDescription);
      setTestedEntityTypeHint(trimmedEntityTypeHint);
      setTestResults(response.items);
      setTestResultCount(response.total);
    } catch (error) {
      setTestedQuery(trimmedDescription);
      setTestedEntityTypeHint(trimmedEntityTypeHint);
      setTestResults([]);
      setTestResultCount(null);
      if (error instanceof ApiProblemError) {
        setErrorMessage(error.problem.detail);
      } else {
        setErrorMessage("Unable to test that detection query right now.");
      }
    } finally {
      setIsTestingQuery(false);
    }
  }

  async function handleCreateFact(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!writeScopeQuery) {
      setErrorMessage(writeDisabledReason);
      return;
    }

    const evidencePayload = hasCurrentTestResults
      ? testResults
          .map(buildEvidencePayload)
          .filter((item): item is PinnedFactEvidencePayload => item !== null)
      : seededEvidence;
    const sourceDocumentId = hasCurrentTestResults
      ? testResults.map(buildSourceDocumentId).find((value) => value) ?? null
      : locationState?.source_document_id ?? null;

    if (evidencePayload.length === 0) {
      setErrorMessage("Add evidence by testing the query or pinning from a chat answer before creating the fact.");
      return;
    }

    setErrorMessage(null);
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
          description: trimmedDescription,
          entity_type_hint: trimmedEntityTypeHint || null,
          evidence: evidencePayload,
          is_active: true,
          key: trimmedKey,
          source_document_id: sourceDocumentId,
          title: trimmedTitle,
          ...payload
        },
        writeScopeQuery
      );
      navigate("/pinned-facts");
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
        title="Create pinned fact"
        description="Define a pinned fact, confirm the stored value, and save it with the full evidence set that supports it."
        actions={
          <Button asChild type="button" variant="outline">
            <Link to="/pinned-facts">Back to pinned facts</Link>
          </Button>
        }
      />

      {writeDisabledReason ? (
        <Alert variant="info">
          <AlertTitle>Write actions are limited</AlertTitle>
          <AlertDescription>{writeDisabledReason}</AlertDescription>
        </Alert>
      ) : null}

      {locationState ? (
        <Alert variant="info">
          <AlertTitle>Seeded from chat</AlertTitle>
          <AlertDescription>
            {locationState.origin_label
              ? `This draft was seeded from ${locationState.origin_label}. You can create it immediately or rerun the detection query first.`
              : "This draft was seeded from a chat answer. You can create it immediately or rerun the detection query first."}
          </AlertDescription>
        </Alert>
      ) : null}

      {errorMessage ? (
        <Alert variant="destructive">
          <AlertTitle>Pinned-fact action failed</AlertTitle>
          <AlertDescription>{errorMessage}</AlertDescription>
        </Alert>
      ) : null}

      <Card>
        <CardContent className="p-6">
          <form className="space-y-5" onSubmit={handleCreateFact}>
            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="pinned-fact-title">
                Name
              </label>
              <Input
                id="pinned-fact-title"
                required
                disabled={isCreating}
                placeholder="Project color scheme"
                value={title}
                onChange={(event) => setTitle(event.currentTarget.value)}
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="pinned-fact-key">
                Key
              </label>
              <Input
                id="pinned-fact-key"
                required
                disabled={isCreating}
                placeholder="project_color_scheme"
                value={key}
                onChange={(event) => setKey(event.currentTarget.value)}
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="pinned-fact-description">
                Detection query
              </label>
              <Textarea
                id="pinned-fact-description"
                required
                disabled={isCreating}
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
                  <Button
                    type="button"
                    variant={valueKind === "text" ? "default" : "outline"}
                    onClick={() => setValueKind("text")}
                  >
                    Text
                  </Button>
                  <Button
                    type="button"
                    variant={valueKind === "json" ? "default" : "outline"}
                    onClick={() => setValueKind("json")}
                  >
                    JSON
                  </Button>
                </div>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="pinned-fact-value">
                  Stored value
                </label>
                <Textarea
                  id="pinned-fact-value"
                  required
                  disabled={isCreating}
                  rows={4}
                  placeholder={valueKind === "json" ? '{ "primary": "#2563eb" }' : "Atlas"}
                  value={valueInput}
                  onChange={(event) => setValueInput(event.currentTarget.value)}
                />
              </div>
            </div>

            <div className="flex justify-end gap-3">
              <Button
                type="button"
                variant="outline"
                disabled={!isReady || !trimmedDescription || isTestingQuery}
                onClick={handleTestQuery}
              >
                {isTestingQuery ? "Testing…" : "Test Query"}
              </Button>
              <Button disabled={!canCreate} type="submit">
                {isCreating ? "Creating…" : "Create"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {shouldRefreshTestResults ? (
        <Alert variant="info">
          <AlertTitle>Test query results need a refresh</AlertTitle>
          <AlertDescription>
            The detection query changed. Run Test Query again before creating the pinned fact.
          </AlertDescription>
        </Alert>
      ) : null}

      {isTestingQuery ? (
        <p className="text-sm text-muted-foreground">Testing detection query…</p>
      ) : hasCurrentTestResults ? (
        <section className="space-y-4">
          <div className="flex items-center gap-3">
            <h2 className="text-2xl font-semibold tracking-tight">Test query results</h2>
            <Badge variant="outline">{testResultCount ?? testResults.length} matches</Badge>
          </div>
          {testResults.length > 0 ? (
            <div className="space-y-4">
              {testResults.map((item) => (
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
                        <Badge>Included as evidence</Badge>
                        <Badge variant="outline">Score {formatScore(item.score)}</Badge>
                        {item.matched_modes?.map((mode) => (
                          <Badge key={`${item.result_id}-${mode}`} variant="secondary">
                            {formatSearchMode(mode)}
                          </Badge>
                        ))}
                      </div>
                    </div>

                    <p className="leading-7 text-foreground">{item.preview_text}</p>

                    {item.citations.length > 0 ? (
                      <div className="space-y-2 rounded-md border bg-muted/20 p-4">
                        <p className="text-sm font-semibold">Citations</p>
                        {item.citations.map((citation, citationIndex) => (
                          <p key={`${item.result_id}-${citationIndex}`} className="text-sm text-muted-foreground">
                            {formatCitationLabel(citation)} · {formatSourceTier(citation.source_tier)}
                          </p>
                        ))}
                      </div>
                    ) : null}

                    <div className="flex flex-wrap gap-3">
                      {item.document?.id ? (
                        <Button asChild type="button" variant="outline">
                          <Link to={`/documents/${item.document.id}`}>Open document</Link>
                        </Button>
                      ) : null}
                      {item.entity?.id ? (
                        <Button asChild type="button" variant="ghost">
                          <Link to={`/entities/${item.entity.id}`}>Open entity</Link>
                        </Button>
                      ) : null}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              No results match the current detection query and scope.
            </p>
          )}
        </section>
      ) : canUseSeededEvidence ? (
        <section className="space-y-4">
          <div className="flex items-center gap-3">
            <h2 className="text-2xl font-semibold tracking-tight">Seed evidence</h2>
            <Badge variant="outline">{seededEvidence.length} items</Badge>
          </div>
          <div className="space-y-4">
            {seededEvidence.map((item, index) => (
              <Card key={`seeded-evidence-${index}`}>
                  <CardContent className="space-y-3 p-6">
                    <p className="leading-7 text-foreground">{item.quote}</p>
                    {item.citations.map((citation, citationIndex) => (
                      <p key={`seeded-evidence-${index}-${citationIndex}`} className="text-sm text-muted-foreground">
                        {formatCitationLabel(citation)} · {formatSourceTier(citation.source_tier)}
                      </p>
                    ))}
                  </CardContent>
                </Card>
            ))}
          </div>
        </section>
      ) : (
        <Alert variant="info">
          <AlertTitle>Test query is ready</AlertTitle>
          <AlertDescription>
            Run Test Query to preview the full evidence set that will seed this pinned fact.
          </AlertDescription>
        </Alert>
      )}
    </Page>
  );
}
