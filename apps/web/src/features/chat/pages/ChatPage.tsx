import type { ChatMessageRecord } from "@contracts";
import { useState, type FormEvent } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  Group,
  ScrollArea,
  SimpleGrid,
  Stack,
  Text,
  Textarea,
  Title
} from "@mantine/core";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";

import { ApiProblemError } from "../../../shared/api/client";
import {
  formatCitationLabel,
  formatDateTime,
  formatSearchMode,
  formatSourceTier
} from "../../../shared/lib/formatting";
import { useSpaceScope } from "../../../shared/state/spaceScope";
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
    <Stack gap="xl">
      <Stack gap={4}>
        <Title order={2}>Chat</Title>
        <Text c="dimmed">
          Ask retrieval-backed questions, review citations, and submit targeted corrections from assistant answers.
        </Text>
        <Badge color={allSpaces ? "blue" : "teal"} variant="light" w="fit-content">
          {allSpaces ? "Session creation disabled in all-spaces mode" : activeSpace?.name ?? "One active Space"}
        </Badge>
      </Stack>

      {allSpaces ? (
        <Alert color="blue" title="All-spaces mode is on">
          You can read sessions across Spaces, but creating new sessions requires one active Space.
        </Alert>
      ) : null}

      {errorMessage ? (
        <Alert color="red" title="Chat action failed">
          {errorMessage}
        </Alert>
      ) : null}

      {feedbackMessage ? (
        <Alert color="teal" title="Saved">
          {feedbackMessage}
        </Alert>
      ) : null}

      <SimpleGrid cols={{ base: 1, lg: 3 }}>
        <Card withBorder radius="lg" p="lg">
          <Stack gap="md">
            <Group justify="space-between">
              <Title order={4}>Sessions</Title>
              <Button
                disabled={allSpaces}
                loading={isCreatingSession}
                variant="light"
                onClick={() => void handleCreateSession()}
              >
                New session
              </Button>
            </Group>

            {sessionsQuery.error instanceof ApiProblemError ? (
              <Alert color="red" title="Unable to load sessions">
                {sessionsQuery.error.problem.detail}
              </Alert>
            ) : sessionsQuery.isLoading ? (
              <Text c="dimmed">Loading sessions…</Text>
            ) : sessionsQuery.data && sessionsQuery.data.items.length > 0 ? (
              <ScrollArea.Autosize mah={560}>
                <Stack gap="sm">
                  {sessionsQuery.data.items.map((session) => (
                    <Card
                      key={session.id}
                      withBorder
                      p="md"
                      radius="md"
                      style={{
                        borderColor: session.id === sessionId ? "var(--mantine-color-teal-5)" : undefined
                      }}
                    >
                      <Stack gap={6}>
                        <Button
                          component={Link}
                          fullWidth
                          justify="space-between"
                          to={`/chat/${session.id}`}
                          variant={session.id === sessionId ? "light" : "subtle"}
                        >
                          {session.title}
                        </Button>
                        {session.document_id ? (
                          <Badge color="teal" variant="light" w="fit-content">
                            document-first
                          </Badge>
                        ) : null}
                        <Text c="dimmed" size="sm">
                          {session.message_count} messages · updated {formatDateTime(session.updated_at)}
                        </Text>
                      </Stack>
                    </Card>
                  ))}
                </Stack>
              </ScrollArea.Autosize>
            ) : (
              <Text c="dimmed">Create the first chat session to begin asking questions.</Text>
            )}
          </Stack>
        </Card>

        <Card withBorder radius="lg" p="lg" style={{ gridColumn: "span 2" }}>
          <Stack gap="md">
            <Group justify="space-between">
              <Stack gap={2}>
                <Title order={4}>{detailQuery.data?.title ?? "Chat transcript"}</Title>
                <Text c="dimmed" size="sm">
                  {detailQuery.data
                    ? `Session updated ${formatDateTime(detailQuery.data.updated_at)}`
                    : "Select a session from the list or create a new one."}
                </Text>
              </Stack>
              {detailQuery.data ? (
                <Group gap="xs">
                  {detailQuery.data.document_id ? (
                    <Badge color="teal" variant="light">
                      document-first
                    </Badge>
                  ) : null}
                  <Badge variant="light">
                    {detailQuery.data.message_count} messages
                  </Badge>
                </Group>
              ) : null}
            </Group>

            {detailQuery.error instanceof ApiProblemError ? (
              <Alert color="red" title="Unable to load the selected session">
                {detailQuery.error.problem.detail}
              </Alert>
            ) : detailQuery.isLoading ? (
              <Text c="dimmed">Loading chat transcript…</Text>
            ) : detailQuery.data ? (
              <>
                <ScrollArea.Autosize mah={520}>
                  <Stack gap="md">
                    {detailQuery.data.messages?.map((messageRecord) => (
                      <Card key={messageRecord.id} withBorder radius="md" p="md">
                        <Stack gap="sm">
                          <Group justify="space-between" align="start">
                            <Group gap="xs">
                              <Badge color={messageRecord.role === "assistant" ? "teal" : "gray"}>
                                {messageRecord.role}
                              </Badge>
                              {messageRecord.retrieval_mode ? (
                                <Badge variant="light">
                                  {formatSearchMode(messageRecord.retrieval_mode as never)}
                                </Badge>
                              ) : null}
                              {messageRecord.degraded ? (
                                <Badge color="yellow" variant="light">
                                  degraded
                                </Badge>
                              ) : null}
                            </Group>
                            <Text c="dimmed" size="sm">
                              {formatDateTime(messageRecord.created_at)}
                            </Text>
                          </Group>

                          <Text style={{ whiteSpace: "pre-wrap" }}>{messageRecord.content}</Text>

                          {messageRecord.citations && messageRecord.citations.length > 0 ? (
                            <Stack gap={4}>
                              <Text fw={600} size="sm">
                                Citations
                              </Text>
                              {messageRecord.citations.map((citation, index) => (
                                <Text key={`${messageRecord.id}-${index}`} size="sm">
                                  {formatCitationLabel(citation)} · {formatSourceTier(citation.source_tier)}
                                </Text>
                              ))}
                            </Stack>
                          ) : null}

                          {messageRecord.suggestions && messageRecord.suggestions.length > 0 ? (
                            <Stack gap={4}>
                              <Text fw={600} size="sm">
                                Suggestions
                              </Text>
                              {messageRecord.suggestions.map((suggestion) => (
                                <Text key={suggestion.prompt} size="sm">
                                  {suggestion.label}: {suggestion.prompt}
                                </Text>
                              ))}
                            </Stack>
                          ) : null}

                          {messageRecord.role === "assistant" ? (
                            <Stack gap="sm">
                              <Group>
                                <Button
                                  size="xs"
                                  variant="subtle"
                                  onClick={() =>
                                    setOpenCorrectionMessageId(
                                      openCorrectionMessageId === messageRecord.id
                                        ? null
                                        : messageRecord.id
                                    )
                                  }
                                >
                                  Submit correction
                                </Button>
                              </Group>

                              {openCorrectionMessageId === messageRecord.id ? (
                                <Card withBorder radius="md" p="md">
                                  <Stack gap="sm">
                                    <Textarea
                                      label="Proposed correction"
                                      minRows={2}
                                      value={proposedValue}
                                      onChange={(event) => setProposedValue(event.currentTarget.value)}
                                    />
                                    <Textarea
                                      label="Rationale"
                                      minRows={2}
                                      value={rationale}
                                      onChange={(event) => setRationale(event.currentTarget.value)}
                                    />
                                    <Group justify="flex-end">
                                      <Button
                                        loading={isSubmittingCorrection}
                                        size="xs"
                                        onClick={() => void handleSubmitCorrection(messageRecord)}
                                      >
                                        Submit for review
                                      </Button>
                                    </Group>
                                  </Stack>
                                </Card>
                              ) : null}
                            </Stack>
                          ) : null}
                        </Stack>
                      </Card>
                    ))}
                  </Stack>
                </ScrollArea.Autosize>

                <form onSubmit={handleSendMessage}>
                  <Stack gap="sm">
                    <Textarea
                      required
                      label="Message"
                      minRows={3}
                      placeholder="Ask a question grounded in your uploaded material"
                      value={message}
                      onChange={(event) => setMessage(event.currentTarget.value)}
                    />
                    <Group justify="flex-end">
                      <Button loading={isSendingMessage} type="submit">
                        Send message
                      </Button>
                    </Group>
                  </Stack>
                </form>
              </>
            ) : (
              <Text c="dimmed">
                {sessionsQuery.data?.items.length
                  ? "Select a session on the left to open the transcript."
                  : "Create a session to start a retrieval-backed conversation."}
              </Text>
            )}
          </Stack>
        </Card>
      </SimpleGrid>
    </Stack>
  );
}
