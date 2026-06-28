import type { ChatMessageRecord } from "@contracts";
import type { AppendMessage } from "@assistant-ui/react";
import { useCallback, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { Thread } from "@/components/assistant-ui/thread";
import { Page } from "@/components/app/page";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { ApiProblemError } from "@/shared/api/client";
import { formatDateTime, formatRelativeAgeShort } from "@/shared/lib/formatting";
import { useSpaceScope } from "@/shared/state/spaceScope";
import {
  createChatSession,
  createCorrection,
  listChatSessions,
  readChatSession,
  sendChatMessage
} from "../api/chatApi";
import { ChatAssistantMessage } from "../components/ChatAssistantMessage";
import {
  ChatAssistantRuntime,
  extractAppendMessageText
} from "../components/ChatAssistantRuntime";
import { ChatCorrectionDialog } from "../components/ChatCorrectionDialog";

export function ChatPage() {
  const navigate = useNavigate();
  const { sessionId } = useParams<{ sessionId?: string }>();
  const queryClient = useQueryClient();
  const { allSpaces, buildReadScopeParams, isReady, requireConcreteSpace } =
    useSpaceScope();
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

  const sendPrompt = useCallback(
    async (content: string) => {
      const trimmedContent = content.trim();

      if (!trimmedContent) {
        return;
      }

      if (!sessionId) {
        setErrorMessage("Create or select a session before sending a message.");
        return;
      }

      setErrorMessage(null);
      setFeedbackMessage(null);
      setIsSendingMessage(true);
      try {
        const response = await sendChatMessage(sessionId, { content: trimmedContent });
        queryClient.setQueryData(["chat-session", sessionId], response.session);
        await sessionsQuery.refetch();
      } catch (error) {
        if (error instanceof ApiProblemError) {
          setErrorMessage(error.problem.detail);
        } else {
          setErrorMessage("Unable to send that message right now.");
        }
        throw error;
      } finally {
        setIsSendingMessage(false);
      }
    },
    [queryClient, sessionId, sessionsQuery]
  );

  const handleAssistantNewMessage = useCallback(
    async (message: AppendMessage) => {
      await sendPrompt(extractAppendMessageText(message));
    },
    [sendPrompt]
  );

  async function handleSubmitCorrection(messageRecord: ChatMessageRecord) {
    if (!detailQuery.data) {
      return;
    }

    const trimmedProposedValue = proposedValue.trim();
    if (!trimmedProposedValue) {
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
          proposed_value: trimmedProposedValue,
          rationale: rationale.trim() || null,
          pinned_fact_id: null
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

  function handleOpenCorrection(messageRecord: ChatMessageRecord) {
    setOpenCorrectionMessageId(messageRecord.id);
    setProposedValue("");
    setRationale("");
  }

  function handleCorrectionDialogOpenChange(open: boolean) {
    if (!open) {
      setOpenCorrectionMessageId(null);
      setProposedValue("");
      setRationale("");
    }
  }

  const messageById = useMemo(
    () =>
      new Map(
        (detailQuery.data?.messages ?? []).map((messageRecord) => [
          messageRecord.id,
          messageRecord
        ])
      ),
    [detailQuery.data?.messages]
  );
  const selectedCorrectionMessage = openCorrectionMessageId
    ? messageById.get(openCorrectionMessageId) ?? null
    : null;

  return (
    <Page className="flex flex-col gap-4 space-y-0 lg:min-h-0 lg:flex-1">
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

      <section className="grid gap-4 lg:min-h-0 lg:flex-1 lg:grid-cols-[240px_minmax(0,1fr)] lg:grid-rows-[minmax(0,1fr)] lg:overflow-hidden">
        <Card className="flex flex-col lg:h-full lg:min-h-0 lg:overflow-hidden">
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
          <CardContent className="flex flex-col px-3 pb-4 pt-0 lg:min-h-0 lg:flex-1 lg:overflow-hidden">
            {sessionsQuery.error instanceof ApiProblemError ? (
              <Alert variant="destructive">
                <AlertTitle>Unable to load sessions</AlertTitle>
                <AlertDescription>{sessionsQuery.error.problem.detail}</AlertDescription>
              </Alert>
            ) : sessionsQuery.isLoading ? (
              <p className="text-sm text-muted-foreground">Loading sessions…</p>
            ) : sessionsQuery.data && sessionsQuery.data.items.length > 0 ? (
              <ScrollArea className="min-w-0 pr-2 lg:min-h-0 lg:flex-1">
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

        <Card className="flex flex-col lg:h-full lg:min-h-0 lg:overflow-hidden">
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
          <CardContent className="flex flex-col lg:min-h-0 lg:flex-1 lg:overflow-hidden">
            {detailQuery.error instanceof ApiProblemError ? (
              <Alert variant="destructive">
                <AlertTitle>Unable to load the selected session</AlertTitle>
                <AlertDescription>{detailQuery.error.problem.detail}</AlertDescription>
              </Alert>
            ) : detailQuery.isLoading ? (
              <p className="text-sm text-muted-foreground">Loading chat transcript…</p>
            ) : detailQuery.data ? (
              <>
                <div className="overflow-hidden rounded-md border bg-background lg:min-h-0 lg:flex-1">
                  <ChatAssistantRuntime
                    isLoading={detailQuery.isLoading}
                    isRunning={isSendingMessage}
                    isSendDisabled={isSendingMessage || !sessionId}
                    messages={detailQuery.data.messages ?? []}
                    onNew={handleAssistantNewMessage}
                  >
                    <Thread
                      components={{
                        AssistantMessage: () => (
                          <ChatAssistantMessage
                            messageById={messageById}
                            onOpenCorrection={handleOpenCorrection}
                          />
                        )
                      }}
                    />
                  </ChatAssistantRuntime>
                </div>

                <ChatCorrectionDialog
                  isSubmitting={isSubmittingCorrection}
                  message={selectedCorrectionMessage}
                  proposedValue={proposedValue}
                  rationale={rationale}
                  onOpenChange={handleCorrectionDialogOpenChange}
                  onProposedValueChange={setProposedValue}
                  onRationaleChange={setRationale}
                  onSubmit={(messageRecord) => void handleSubmitCorrection(messageRecord)}
                />
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
