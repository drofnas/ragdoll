import type { ChatMessageRecord, Citation, SearchResult } from "@contracts";
import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { Page, PageHeader } from "@/components/app/page";
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
import type { PinnedFactEvidencePayload } from "../api/pinnedFactsApi";
import { createPinnedFact, previewPinnedFactDetection } from "../api/pinnedFactsApi";

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

function formatInitialValueInput(locationState: CreatePageLocationState["draft"] | undefined) {
  if (!locationState) {
    return "";
  }
  if (locationState.value_kind === "json") {
    return JSON.stringify(locationState.value_json ?? {}, null, 2);
  }
  return locationState.value_text ?? "";
}

function inferStoredValuePayload(valueInput: string) {
  const trimmed = valueInput.trim();
  if (!trimmed) {
    throw new SyntaxError("Enter a stored value before creating the pinned fact.");
  }
  if (trimmed.startsWith("{")) {
    const parsed = JSON.parse(trimmed) as unknown;
    if (parsed === null || Array.isArray(parsed) || typeof parsed !== "object") {
      throw new TypeError("Stored JSON values must be objects.");
    }
    return {
      value_json: parsed as Record<string, unknown>,
      value_kind: "json" as const,
      value_text: null
    };
  }
  return {
    value_json: null,
    value_kind: "text" as const,
    value_text: trimmed
  };
}

function stripInlineEvidenceMarkers(value: string) {
  return value
    .replace(/\s*\[E\d+\]/g, "")
    .split("\n")
    .map((line) => line.replace(/\s+$/g, ""))
    .join("\n")
    .trim();
}

function unwrapSingleFencedBlock(value: string) {
  const match = value.match(/^\s*```(?:[a-zA-Z0-9_-]+)?\s*\n?(.*?)\n?```\s*$/s);
  return match ? match[1].trim() : value.trim();
}

function normalizeAssistantAnswer(value: string) {
  return stripInlineEvidenceMarkers(unwrapSingleFencedBlock(value));
}

function citationSignature(citation: Citation) {
  return [
    citation.document_id ?? "",
    citation.entity_id ?? "",
    citation.chunk_id ?? "",
    citation.locator ?? "",
    citation.line_number ?? "",
    citation.source_tier ?? "",
    citation.title ?? ""
  ].join("|");
}

function deriveEvidenceFromAssistantMessage(message: ChatMessageRecord | null): PinnedFactEvidencePayload[] {
  if (!message) {
    return [];
  }

  const evidenceById = new Map((message.evidence ?? []).map((item) => [item.id, item]));
  const citedIds = Array.from(
    new Set(Array.from(message.content.matchAll(/\[(E\d+)\]/g), (match) => match[1]))
  );
  const selectedById = citedIds.map((id) => evidenceById.get(id)).filter((item) => item !== undefined);

  const selectedEvidence =
    selectedById.length > 0
      ? selectedById
      : (() => {
          const citationSet = new Set((message.citations ?? []).map((citation) => citationSignature(citation)));
          if (citationSet.size === 0) {
            return [];
          }
          return (message.evidence ?? []).filter((item) =>
            (item.citations ?? []).some((citation) => citationSet.has(citationSignature(citation)))
          );
        })();

  const deduped = new Map(
    selectedEvidence.map((item) => [
      JSON.stringify({
        citations: item.citations ?? [],
        quote: item.text,
        source_chunk_ids: (item.citations ?? [])
          .map((citation) => citation.chunk_id)
          .filter((chunkId): chunkId is string => Boolean(chunkId))
          .sort()
      }),
      {
        citations: item.citations ?? [],
        quote: item.text,
        source_chunk_ids: (item.citations ?? [])
          .map((citation) => citation.chunk_id)
          .filter((chunkId): chunkId is string => Boolean(chunkId))
          .sort()
      } satisfies PinnedFactEvidencePayload
    ])
  );

  return Array.from(deduped.values());
}

function deriveSourceDocumentId(evidence: PinnedFactEvidencePayload[]) {
  const documentIds = new Set(
    evidence.flatMap((item) =>
      item.citations
        .map((citation) => citation.document_id)
        .filter((documentId): documentId is string => Boolean(documentId))
    )
  );
  return documentIds.size === 1 ? Array.from(documentIds)[0] : null;
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
  const [valueInput, setValueInput] = useState(formatInitialValueInput(locationState));
  const [testedQuery, setTestedQuery] = useState("");
  const [testedEntityTypeHint, setTestedEntityTypeHint] = useState("");
  const [testAssistantMessage, setTestAssistantMessage] = useState<ChatMessageRecord | null>(null);
  const [testResults, setTestResults] = useState<SearchResult[]>([]);
  const [testEvidence, setTestEvidence] = useState<PinnedFactEvidencePayload[]>([]);
  const [testSourceDocumentId, setTestSourceDocumentId] = useState<string | null>(null);
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
  const hasCurrentPreview = hasCurrentTestResults && testAssistantMessage !== null;
  const hasCurrentPreviewEvidence = hasCurrentPreview && testEvidence.length > 0;
  const seededEvidence = locationState?.evidence ?? [];
  const canUseSeededEvidence = seededEvidence.length > 0 && !hasCurrentPreviewEvidence;
  const isFormValid =
    trimmedKey.length > 0 &&
    trimmedTitle.length > 0 &&
    trimmedDescription.length > 0 &&
    valueInput.trim().length > 0;
  const canCreate = Boolean(writeScopeQuery && isFormValid && !isCreating);
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
      const response = await previewPinnedFactDetection(
        {
          description: trimmedDescription,
          entity_type_hint: trimmedEntityTypeHint || undefined
        },
        readScopeQuery
      );
      const derivedEvidence = deriveEvidenceFromAssistantMessage(response.assistant_message);
      setTestedQuery(trimmedDescription);
      setTestedEntityTypeHint(trimmedEntityTypeHint);
      setTestAssistantMessage(response.assistant_message);
      setTestResults(response.retrieval_results);
      setTestEvidence(derivedEvidence);
      setTestSourceDocumentId(response.source_document_id ?? deriveSourceDocumentId(derivedEvidence));
      setTestResultCount(response.retrieval_results.length);
    } catch (error) {
      setTestedQuery(trimmedDescription);
      setTestedEntityTypeHint(trimmedEntityTypeHint);
      setTestAssistantMessage(null);
      setTestResults([]);
      setTestEvidence([]);
      setTestSourceDocumentId(null);
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

    const evidencePayload = hasCurrentPreviewEvidence ? testEvidence : seededEvidence;
    const sourceDocumentId = hasCurrentPreviewEvidence
      ? testSourceDocumentId
      : locationState?.source_document_id ?? null;

    if (evidencePayload.length === 0) {
      setErrorMessage("Add evidence by testing the query or pinning from a chat answer before creating the fact.");
      return;
    }

    setErrorMessage(null);
    setIsCreating(true);

    try {
      const payload = inferStoredValuePayload(valueInput);

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
      if (error instanceof TypeError) {
        setErrorMessage(error.message);
      } else if (error instanceof SyntaxError) {
        setErrorMessage(error.message || "JSON values must be valid JSON before the fact can be created.");
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

            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="pinned-fact-value">
                Stored value
              </label>
              <Textarea
                id="pinned-fact-value"
                required
                disabled={isCreating}
                rows={5}
                placeholder="Atlas or { &quot;technology_stack&quot;: [&quot;React&quot;, &quot;Vite&quot;] }"
                value={valueInput}
                onChange={(event) => setValueInput(event.currentTarget.value)}
              />
              <p className="text-sm text-muted-foreground">
                JSON objects will be detected automatically. Any other stored value is saved as text.
              </p>
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
            <h2 className="text-2xl font-semibold tracking-tight">Detection preview</h2>
            <Badge variant="outline">{testResultCount ?? testResults.length} matches</Badge>
          </div>
          {testAssistantMessage ? (
            <Card>
              <CardContent className="space-y-4 p-6">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">Assistant preview</Badge>
                    {testAssistantMessage.degraded ? <Badge variant="secondary">Degraded fallback</Badge> : null}
                  </div>
                  <Button
                    type="button"
                    onClick={() => setValueInput(normalizeAssistantAnswer(testAssistantMessage.content))}
                  >
                    Use as Stored Value
                  </Button>
                </div>
                <pre className="whitespace-pre-wrap break-words rounded-md border bg-muted/20 p-4 text-sm leading-6 text-foreground">
                  {testAssistantMessage.content}
                </pre>
                {testAssistantMessage.citations.length > 0 ? (
                  <div className="space-y-2 rounded-md border bg-muted/20 p-4">
                    <p className="text-sm font-semibold">Citations</p>
                    {testAssistantMessage.citations.map((citation, citationIndex) => (
                      <p key={`assistant-preview-citation-${citationIndex}`} className="text-sm text-muted-foreground">
                        {formatCitationLabel(citation)} · {formatSourceTier(citation.source_tier)}
                      </p>
                    ))}
                  </div>
                ) : null}
              </CardContent>
            </Card>
          ) : null}
          {hasCurrentPreviewEvidence ? (
            <section className="space-y-4">
              <div className="flex items-center gap-3">
                <h3 className="text-xl font-semibold tracking-tight">Preview evidence</h3>
                <Badge variant="outline">{testEvidence.length} items</Badge>
              </div>
              <div className="space-y-4">
                {testEvidence.map((item, index) => (
                  <Card key={`test-evidence-${index}`}>
                    <CardContent className="space-y-3 p-6">
                      <Badge>Used for synthesis</Badge>
                      <p className="leading-7 text-foreground">{item.quote}</p>
                      {item.citations.map((citation, citationIndex) => (
                        <p key={`test-evidence-${index}-${citationIndex}`} className="text-sm text-muted-foreground">
                          {formatCitationLabel(citation)} · {formatSourceTier(citation.source_tier)}
                        </p>
                      ))}
                    </CardContent>
                  </Card>
                ))}
              </div>
            </section>
          ) : null}
          <Accordion type="single" collapsible>
            <AccordionItem value="raw-retrieval-results">
              <AccordionTrigger>
                <div className="flex items-center gap-3 text-left">
                  <span className="text-xl font-semibold tracking-tight">Raw retrieval results</span>
                  <Badge variant="outline">{testResults.length}</Badge>
                </div>
              </AccordionTrigger>
              <AccordionContent className="space-y-4 pt-2">
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
                              <Badge>{hasCurrentPreviewEvidence ? "Supporting result" : "Retrieved result"}</Badge>
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
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        </section>
      ) : canUseSeededEvidence ? (
        <section className="space-y-4">
          <div className="flex items-center gap-3">
            <h2 className="text-2xl font-semibold tracking-tight">Seed evidence</h2>
            <Badge variant="outline">{seededEvidence.length} items</Badge>
          </div>
          {!hasCurrentPreviewEvidence && testAssistantMessage !== null ? (
            <Alert variant="info">
              <AlertTitle>Using chat-seeded value</AlertTitle>
              <AlertDescription>
                This draft can still use its chat-seeded stored value and evidence if you create it now.
              </AlertDescription>
            </Alert>
          ) : null}
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
