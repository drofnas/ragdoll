import type { ChatMessageRecord } from "@contracts";
import { useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { Page, PageHeader } from "@/components/app/page";
import { StatusBadge } from "@/components/app/status-badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { ApiProblemError } from "@/shared/api/client";
import {
  formatCitationLabel,
  formatDateTime,
  formatRelativeAgeShort,
  formatSourceTier
} from "@/shared/lib/formatting";
import { useSpaceScope } from "@/shared/state/spaceScope";
import {
  createChatSession,
  createCorrection,
  listChatSessions,
  readChatSession,
  sendChatMessage
} from "../api/chatApi";

export function ChatPage() {
  const navigate = useNavigate();
  const { sessionId } = useParams<{ sessionId?: string }>();
  const { activeSpace, allSpaces, buildReadScopeParams, isReady, requireConcreteSpace } =
    useSpaceScope();
  const [message, setMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);
  const [isCreatingSession, setIsCreatingSession] = useState(false);
  const [isSendingMessage, setIsSendingMessage] = useState(false);
  const [openCorrectionMessageId, setOpenCorrectionMessageId] = useState<string | null>(null);
  const [proposedValue, setProposedValue] = useState("");
  const [rationale, setRationale] = useState("");
  const [isSubmittingCorrection, setIsSubmittingCorrection] = useState(false);

  const scopeQuery = buildReadScopeParams();
  const sessionsQuery = useQuery({
    enabled: isReady,
    queryFn: () =>
      listChatSessions({
        page: 1,
        page_size: 25,
        ...scopeQuery
      }),
    queryKey: ["chat-sessions", scopeQuery]
  });

  const detailQuery = useQuery({
    enabled: Boolean(sessionId),
    queryFn: () => readChatSession(sessionId!),
    queryKey: ["chat-session", sessionId]
  });

  async function handleCreateSession() {
    setErrorMessage(null);
    setFeedbackMessage(null);
    setIsCreatingSession(true);
    try {
      const nextSpace = requireConcreteSpace();
      const session = await createChatSession({ space_id: nextSpace.id });
      await sessionsQuery.refetch();
      navigate(`/chat/${session.id}`);
    } catch (error) {
      if (error instanceof ApiProblemError) {
        setErrorMessage(error.problem.detail);
      } else if (error instanceof Error) {
        setErrorMessage(error.message);
      } else {
        setErrorMessage("Unable to create a chat session right now.");
      }
    } finally {
      setIsCreatingSession(false);
    }
  }

  async function handleSendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!sessionId) {
      setErrorMessage("Create or select a session before sending a message.");
      return;
    }

    setErrorMessage(null);
    setFeedbackMessage(null);
    setIsSendingMessage(true);
    try {
      await sendChatMessage(sessionId, { content: message });
      setMessage("");
      await Promise.all([detailQuery.refetch(), sessionsQuery.refetch()]);
    } catch (error) {
      if (error instanceof ApiProblemError) {
        setErrorMessage(error.problem.detail);
      } else {
        setErrorMessage("Unable to send that message right now.");
      }
    } finally {
      setIsSendingMessage(false);
    }
  }

  async function handleSubmitCorrection(messageRecord: ChatMessageRecord) {
    if (!detailQuery.data) {
      return;
    }

    setErrorMessage(null);
    setFeedbackMessage(null);
    setIsSubmittingCorrection(true);
    const citation = messageRecord.citations?.[0];

    try {
      await createCorrection(
        {
          chat_message_id: messageRecord.id,
          chat_session_id: detailQuery.data.id,
          document_id: citation?.document_id ?? null,
          entity_id: citation?.entity_id ?? null,
          locator_text: citation?.locator ?? null,
          proposed_value: proposedValue,
          rationale: rationale || null,
          tracked_field_id: null
        },
        { space_id: detailQuery.data.space_id }
      );
      setFeedbackMessage("Correction submitted for review.");
      setOpenCorrectionMessageId(null);
      setProposedValue("");
      setRationale("");
    } catch (error) {
      if (error instanceof ApiProblemError) {
        setErrorMessage(error.problem.detail);
      } else {
        setErrorMessage("Unable to submit that correction right now.");
      }
    } finally {
      setIsSubmittingCorrection(false);
    }
  }

  return (
    <Page>
      <PageHeader
        eyebrow="Retrieval chat"
        title="Chat"
        description="Ask retrieval-backed questions, review citations, and submit targeted corrections from assistant answers."
      />

      {allSpaces ? (
        <Alert variant="info">
          <AlertTitle>All-spaces mode is on</AlertTitle>
          <AlertDescription>
            You can read sessions across Spaces, but creating new sessions requires one active Space.
          </AlertDescription>
        </Alert>
      ) : null}

      {errorMessage ? (
        <Alert variant="destructive">
          <AlertTitle>Chat action failed</AlertTitle>
          <AlertDescription>{errorMessage}</AlertDescription>
        </Alert>
      ) : null}

      {feedbackMessage ? (
        <Alert variant="success">
          <AlertTitle>Saved</AlertTitle>
          <AlertDescription>{feedbackMessage}</AlertDescription>
        </Alert>
      ) : null}

      <section className="grid gap-4 lg:grid-cols-[240px_minmax(0,1fr)]">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-2 space-y-0 p-4">
            <CardTitle className="text-lg">Sessions</CardTitle>
            <Button
              className="h-8 px-2.5"
              disabled={allSpaces}
              size="sm"
              variant="outline"
              onClick={() => void handleCreateSession()}
            >
              {isCreatingSession ? "Creating…" : "New session"}
            </Button>
          </CardHeader>
          <CardContent className="px-3 pb-4 pt-0">
            {sessionsQuery.error instanceof ApiProblemError ? (
              <Alert variant="destructive">
                <AlertTitle>Unable to load sessions</AlertTitle>
                <AlertDescription>{sessionsQuery.error.problem.detail}</AlertDescription>
              </Alert>
            ) : sessionsQuery.isLoading ? (
              <p className="text-sm text-muted-foreground">Loading sessions…</p>
            ) : sessionsQuery.data && sessionsQuery.data.items.length > 0 ? (
              <ScrollArea className="h-[35rem] min-w-0 pr-2">
                <div className="min-w-0 space-y-1">
                  {sessionsQuery.data.items.map((session) => {
                    const isSelected = session.id === sessionId;
                    const updatedAt = formatDateTime(session.updated_at);

                    return (
                      <Link
                        aria-label={`${session.title}, updated ${updatedAt}`}
                        className={cn(
                          buttonVariants({
                            size: "sm",
                            variant: isSelected ? "default" : "ghost"
                          }),
                          "grid w-full max-w-full grid-cols-[minmax(0,1fr)_auto] items-center gap-2 overflow-hidden px-2 text-left"
                        )}
                        key={session.id}
                        title={`${session.title} · updated ${updatedAt}`}
                        to={`/chat/${session.id}`}
                      >
                        <span className="block min-w-0 truncate text-left">{session.title}</span>
                        <span
                          className={cn(
                            "justify-self-end text-right text-xs tabular-nums",
                            isSelected ? "text-primary-foreground/80" : "text-muted-foreground"
                          )}
                        >
                          {formatRelativeAgeShort(session.updated_at)}
                        </span>
                      </Link>
                    );
                  })}
                </div>
              </ScrollArea>
            ) : (
              <p className="text-sm text-muted-foreground">
                Create the first chat session to begin asking questions.
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-start justify-between gap-4 space-y-0">
            <div className="space-y-2">
              <CardTitle>{detailQuery.data?.title ?? "Chat transcript"}</CardTitle>
              <p className="text-sm text-muted-foreground">
                {detailQuery.data
                  ? `Session updated ${formatDateTime(detailQuery.data.updated_at)}`
                  : "Select a session from the list or create a new one."}
              </p>
            </div>
            {detailQuery.data ? (
              <div className="flex flex-wrap gap-2">
                {detailQuery.data.document_id ? <Badge>document-first</Badge> : null}
                <Badge variant="outline">{detailQuery.data.message_count} messages</Badge>
              </div>
            ) : null}
          </CardHeader>
          <CardContent className="space-y-5">
            {detailQuery.error instanceof ApiProblemError ? (
              <Alert variant="destructive">
                <AlertTitle>Unable to load the selected session</AlertTitle>
                <AlertDescription>{detailQuery.error.problem.detail}</AlertDescription>
              </Alert>
            ) : detailQuery.isLoading ? (
              <p className="text-sm text-muted-foreground">Loading chat transcript…</p>
            ) : detailQuery.data ? (
              <>
                <ScrollArea className="h-[32rem] rounded-md border bg-muted/20 p-4">
                  <div className="space-y-4 pr-3">
                    {detailQuery.data.messages?.map((messageRecord) => (
                      <Card key={messageRecord.id} className="shadow-none">
                        <CardContent className="space-y-4 p-5">
                          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                            <StatusBadge label={messageRecord.role} value={messageRecord.role === "assistant" ? "active" : "inactive"} />
                            <p className="text-sm text-muted-foreground">
                              {formatDateTime(messageRecord.created_at)}
                            </p>
                          </div>

                          <p className="whitespace-pre-wrap leading-7 text-foreground">
                            {messageRecord.content}
                          </p>

                          {messageRecord.citations && messageRecord.citations.length > 0 ? (
                            <div className="space-y-2 rounded-md border bg-muted/20 p-4">
                              <p className="text-sm font-semibold">Citations</p>
                              {messageRecord.citations.map((citation, index) => (
                                <p key={`${messageRecord.id}-${index}`} className="text-sm text-muted-foreground">
                                  {formatCitationLabel(citation)} · {formatSourceTier(citation.source_tier)}
                                </p>
                              ))}
                            </div>
                          ) : null}

                          {messageRecord.role === "assistant" ? (
                            <div className="space-y-3">
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() =>
                                  setOpenCorrectionMessageId(
                                    openCorrectionMessageId === messageRecord.id ? null : messageRecord.id
                                  )
                                }
                              >
                                Submit correction
                              </Button>

                              {openCorrectionMessageId === messageRecord.id ? (
                                <Card className="bg-muted/20 shadow-none">
                                  <CardContent className="space-y-4 p-5">
                                    <div className="space-y-2">
                                      <label
                                        className="text-sm font-medium"
                                        htmlFor={`proposed-correction-${messageRecord.id}`}
                                      >
                                        Proposed correction
                                      </label>
                                      <Textarea
                                        id={`proposed-correction-${messageRecord.id}`}
                                        rows={3}
                                        value={proposedValue}
                                        onChange={(event) => setProposedValue(event.currentTarget.value)}
                                      />
                                    </div>
                                    <div className="space-y-2">
                                      <label
                                        className="text-sm font-medium"
                                        htmlFor={`correction-rationale-${messageRecord.id}`}
                                      >
                                        Rationale
                                      </label>
                                      <Textarea
                                        id={`correction-rationale-${messageRecord.id}`}
                                        rows={3}
                                        value={rationale}
                                        onChange={(event) => setRationale(event.currentTarget.value)}
                                      />
                                    </div>
                                    <div className="flex justify-end">
                                      <Button
                                        size="sm"
                                        onClick={() => void handleSubmitCorrection(messageRecord)}
                                      >
                                        {isSubmittingCorrection ? "Submitting…" : "Submit for review"}
                                      </Button>
                                    </div>
                                  </CardContent>
                                </Card>
                              ) : null}
                            </div>
                          ) : null}
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </ScrollArea>

                <form className="space-y-3" onSubmit={handleSendMessage}>
                  <div className="space-y-2">
                    <label className="text-sm font-medium" htmlFor="chat-message">
                      Message
                    </label>
                    <Textarea
                      id="chat-message"
                      required
                      rows={4}
                      placeholder="Ask a question grounded in your uploaded material"
                      value={message}
                      onChange={(event) => setMessage(event.currentTarget.value)}
                    />
                  </div>
                  <div className="flex justify-end">
                    <Button type="submit">{isSendingMessage ? "Sending…" : "Send message"}</Button>
                  </div>
                </form>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">
                {sessionsQuery.data?.items.length
                  ? "Select a session on the left to open the transcript."
                  : "Create a session to start a retrieval-backed conversation."}
              </p>
            )}
          </CardContent>
        </Card>
      </section>
    </Page>
  );
}
