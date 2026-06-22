import { useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  Group,
  Pagination,
  Select,
  SimpleGrid,
  Stack,
  Tabs,
  Text,
  Textarea,
  Title
} from "@mantine/core";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";

import { ApiProblemError } from "../../../shared/api/client";
import {
  formatCitationLabel,
  formatDateTime,
  formatSourceTier
} from "../../../shared/lib/formatting";
import { useSpaceScope } from "../../../shared/state/spaceScope";
import {
  listChanges,
  listCorrections,
  markChangeRead,
  readChangeDetail,
  readCorrectionDetail,
  rejectCorrection,
  verifyCorrection
} from "../api/changesApi";

const CORRECTION_STATUS_OPTIONS = [
  { label: "All statuses", value: "" },
  { label: "Pending", value: "pending" },
  { label: "Verified", value: "verified" },
  { label: "Rejected", value: "rejected" }
];

export function ChangesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { buildReadScopeParams, isReady } = useSpaceScope();
  const [reviewNotes, setReviewNotes] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);
  const [isMarkingRead, setIsMarkingRead] = useState(false);
  const [reviewAction, setReviewAction] = useState<"verify" | "reject" | null>(null);

  const activeTab = searchParams.get("tab") === "corrections" ? "corrections" : "activity";
  const changeId = searchParams.get("change_id");
  const correctionId = searchParams.get("correction_id");
  const correctionStatus = searchParams.get("status") ?? "";
  const changePage = Math.max(1, Number(searchParams.get("changes_page") ?? "1") || 1);
  const correctionsPage = Math.max(
    1,
    Number(searchParams.get("corrections_page") ?? "1") || 1
  );
  const scopeQuery = buildReadScopeParams();

  function updateParams(updates: Record<string, string | null | undefined>) {
    const next = new URLSearchParams(searchParams);
    for (const [key, value] of Object.entries(updates)) {
      if (!value) {
        next.delete(key);
      } else {
        next.set(key, value);
      }
    }
    setSearchParams(next);
  }

  const changesQuery = useQuery({
    enabled: isReady,
    queryFn: () =>
      listChanges({
        page: changePage,
        page_size: 10,
        ...scopeQuery
      }),
    queryKey: ["changes", changePage, scopeQuery]
  });

  const changeDetailQuery = useQuery({
    enabled: Boolean(changeId),
    queryFn: () => readChangeDetail(changeId!),
    queryKey: ["change-detail", changeId]
  });

  const correctionsQuery = useQuery({
    enabled: isReady,
    queryFn: () =>
      listCorrections({
        page: correctionsPage,
        page_size: 10,
        status: correctionStatus || undefined,
        ...scopeQuery
      }),
    queryKey: ["corrections", correctionsPage, correctionStatus, scopeQuery]
  });

  const correctionDetailQuery = useQuery({
    enabled: Boolean(correctionId),
    queryFn: () => readCorrectionDetail(correctionId!),
    queryKey: ["correction-detail", correctionId]
  });

  async function handleMarkRead() {
    if (!changeId) {
      return;
    }

    setIsMarkingRead(true);
    setErrorMessage(null);
    setFeedbackMessage(null);
    try {
      await markChangeRead(changeId);
      setFeedbackMessage("Change marked as read.");
      await Promise.all([changesQuery.refetch(), changeDetailQuery.refetch()]);
    } catch (error) {
      if (error instanceof ApiProblemError) {
        setErrorMessage(error.problem.detail);
      } else {
        setErrorMessage("Unable to mark that change as read right now.");
      }
    } finally {
      setIsMarkingRead(false);
    }
  }

  async function handleReview(action: "verify" | "reject") {
    if (!correctionId) {
      return;
    }

    setReviewAction(action);
    setErrorMessage(null);
    setFeedbackMessage(null);
    try {
      if (action === "verify") {
        await verifyCorrection(correctionId, { review_notes: reviewNotes || null });
      } else {
        await rejectCorrection(correctionId, { review_notes: reviewNotes || null });
      }
      setFeedbackMessage(
        action === "verify" ? "Correction verified." : "Correction rejected."
      );
      await Promise.all([correctionsQuery.refetch(), correctionDetailQuery.refetch()]);
    } catch (error) {
      if (error instanceof ApiProblemError) {
        setErrorMessage(error.problem.detail);
      } else {
        setErrorMessage("Unable to review that correction right now.");
      }
    } finally {
      setReviewAction(null);
    }
  }

  return (
    <Stack gap="xl">
      <Stack gap={4}>
        <Title order={2}>Changes</Title>
        <Text c="dimmed">
          Review activity updates, inspect change details, and manage correction review from one place.
        </Text>
      </Stack>

      {errorMessage ? (
        <Alert color="red" title="Changes action failed">
          {errorMessage}
        </Alert>
      ) : null}

      {feedbackMessage ? (
        <Alert color="teal" title="Saved">
          {feedbackMessage}
        </Alert>
      ) : null}

      <Tabs
        value={activeTab}
        onChange={(value) =>
          updateParams({
            tab: value ?? "activity"
          })
        }
      >
        <Tabs.List>
          <Tabs.Tab value="activity">Activity</Tabs.Tab>
          <Tabs.Tab value="corrections">Corrections</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="activity" pt="lg">
          <SimpleGrid cols={{ base: 1, lg: 2 }}>
            <Card withBorder radius="lg" p="lg">
              <Stack gap="md">
                <Group justify="space-between">
                  <Title order={4}>Activity feed</Title>
                  <Badge variant="light">{changesQuery.data?.total ?? 0} events</Badge>
                </Group>

                {changesQuery.error instanceof ApiProblemError ? (
                  <Alert color="red" title="Unable to load changes">
                    {changesQuery.error.problem.detail}
                  </Alert>
                ) : changesQuery.isLoading ? (
                  <Text c="dimmed">Loading change events…</Text>
                ) : changesQuery.data && changesQuery.data.items.length > 0 ? (
                  <>
                    <Stack gap="sm">
                      {changesQuery.data.items.map((item) => (
                        <Card
                          key={item.id}
                          withBorder
                          radius="md"
                          p="sm"
                          style={{
                            borderColor:
                              item.id === changeId ? "var(--mantine-color-teal-5)" : undefined
                          }}
                        >
                          <Stack gap={4}>
                            <Group justify="space-between" align="start">
                              <Stack gap={2}>
                                <Button
                                  size="compact-sm"
                                  variant="subtle"
                                  onClick={() =>
                                    updateParams({
                                      change_id: item.id,
                                      tab: "activity"
                                    })
                                  }
                                >
                                  {item.title}
                                </Button>
                                <Text c="dimmed" size="sm">
                                  {item.summary}
                                </Text>
                              </Stack>
                              <Badge color={item.is_read ? "gray" : "teal"} variant="light">
                                {item.is_read ? "read" : "unread"}
                              </Badge>
                            </Group>
                            <Text c="dimmed" size="sm">
                              {formatDateTime(item.created_at)}
                            </Text>
                          </Stack>
                        </Card>
                      ))}
                    </Stack>
                    <Group justify="center">
                      <Pagination
                        total={Math.max(1, Math.ceil(changesQuery.data.total / changesQuery.data.page_size))}
                        value={changePage}
                        onChange={(nextPage) =>
                          updateParams({ changes_page: String(nextPage) })
                        }
                      />
                    </Group>
                  </>
                ) : (
                  <Text c="dimmed">No change events are available for this scope yet.</Text>
                )}
              </Stack>
            </Card>

            <Card withBorder radius="lg" p="lg">
              <Stack gap="md">
                <Group justify="space-between">
                  <Title order={4}>Change detail</Title>
                  {changeDetailQuery.data ? (
                    <Badge color={changeDetailQuery.data.is_read ? "gray" : "teal"} variant="light">
                      {changeDetailQuery.data.is_read ? "read" : "unread"}
                    </Badge>
                  ) : null}
                </Group>

                {changeDetailQuery.error instanceof ApiProblemError ? (
                  <Alert color="red" title="Unable to load change detail">
                    {changeDetailQuery.error.problem.detail}
                  </Alert>
                ) : changeDetailQuery.isLoading ? (
                  <Text c="dimmed">Loading change detail…</Text>
                ) : changeDetailQuery.data ? (
                  <>
                    <Stack gap="xs">
                      <Title order={5}>{changeDetailQuery.data.title}</Title>
                      <Text>{changeDetailQuery.data.summary}</Text>
                      <Text c="dimmed" size="sm">
                        Event type: {changeDetailQuery.data.event_type} · {formatDateTime(changeDetailQuery.data.created_at)}
                      </Text>
                      {changeDetailQuery.data.payload ? (
                        <Card withBorder radius="md" p="sm">
                          <Text size="sm">{JSON.stringify(changeDetailQuery.data.payload, null, 2)}</Text>
                        </Card>
                      ) : null}
                    </Stack>
                    <Group justify="flex-end">
                      <Button
                        loading={isMarkingRead}
                        variant="light"
                        onClick={() => void handleMarkRead()}
                      >
                        Mark read
                      </Button>
                    </Group>
                  </>
                ) : (
                  <Text c="dimmed">Choose an activity item to inspect its detail.</Text>
                )}
              </Stack>
            </Card>
          </SimpleGrid>
        </Tabs.Panel>

        <Tabs.Panel value="corrections" pt="lg">
          <SimpleGrid cols={{ base: 1, lg: 2 }}>
            <Card withBorder radius="lg" p="lg">
              <Stack gap="md">
                <Group justify="space-between">
                  <Title order={4}>Corrections</Title>
                  <Badge variant="light">{correctionsQuery.data?.total ?? 0} records</Badge>
                </Group>
                <Select
                  data={CORRECTION_STATUS_OPTIONS}
                  label="Status filter"
                  value={correctionStatus}
                  onChange={(value) =>
                    updateParams({
                      corrections_page: "1",
                      status: value ?? ""
                    })
                  }
                />

                {correctionsQuery.error instanceof ApiProblemError ? (
                  <Alert color="red" title="Unable to load corrections">
                    {correctionsQuery.error.problem.detail}
                  </Alert>
                ) : correctionsQuery.isLoading ? (
                  <Text c="dimmed">Loading corrections…</Text>
                ) : correctionsQuery.data && correctionsQuery.data.items.length > 0 ? (
                  <>
                    <Stack gap="sm">
                      {correctionsQuery.data.items.map((item) => (
                        <Card
                          key={item.id}
                          withBorder
                          radius="md"
                          p="sm"
                          style={{
                            borderColor:
                              item.id === correctionId ? "var(--mantine-color-teal-5)" : undefined
                          }}
                        >
                          <Stack gap={4}>
                            <Group justify="space-between" align="start">
                              <Stack gap={2}>
                                <Button
                                  size="compact-sm"
                                  variant="subtle"
                                  onClick={() =>
                                    updateParams({
                                      correction_id: item.id,
                                      tab: "corrections"
                                    })
                                  }
                                >
                                  {item.proposed_value}
                                </Button>
                                <Text c="dimmed" size="sm">
                                  {item.rationale ?? "No rationale provided"}
                                </Text>
                              </Stack>
                              <Badge variant="light">{item.status}</Badge>
                            </Group>
                            <Text c="dimmed" size="sm">
                              {formatDateTime(item.created_at)}
                            </Text>
                          </Stack>
                        </Card>
                      ))}
                    </Stack>
                    <Group justify="center">
                      <Pagination
                        total={Math.max(1, Math.ceil(correctionsQuery.data.total / correctionsQuery.data.page_size))}
                        value={correctionsPage}
                        onChange={(nextPage) =>
                          updateParams({ corrections_page: String(nextPage) })
                        }
                      />
                    </Group>
                  </>
                ) : (
                  <Text c="dimmed">No corrections match the current scope and filter.</Text>
                )}
              </Stack>
            </Card>

            <Card withBorder radius="lg" p="lg">
              <Stack gap="md">
                <Title order={4}>Correction detail</Title>
                {correctionDetailQuery.error instanceof ApiProblemError ? (
                  <Alert color="red" title="Unable to load correction detail">
                    {correctionDetailQuery.error.problem.detail}
                  </Alert>
                ) : correctionDetailQuery.isLoading ? (
                  <Text c="dimmed">Loading correction detail…</Text>
                ) : correctionDetailQuery.data ? (
                  <>
                    <Stack gap="xs">
                      <Group justify="space-between">
                        <Title order={5}>{correctionDetailQuery.data.proposed_value}</Title>
                        <Badge variant="light">{correctionDetailQuery.data.status}</Badge>
                      </Group>
                      <Text>{correctionDetailQuery.data.rationale ?? "No rationale provided."}</Text>
                      <Text c="dimmed" size="sm">
                        Submitted {formatDateTime(correctionDetailQuery.data.created_at)}
                      </Text>
                      <Text size="sm">
                        Citation: {formatCitationLabel(correctionDetailQuery.data.citation)} ·{" "}
                        {formatSourceTier(correctionDetailQuery.data.citation.source_tier)}
                      </Text>
                    </Stack>

                    <Textarea
                      label="Review notes"
                      minRows={3}
                      value={reviewNotes}
                      onChange={(event) => setReviewNotes(event.currentTarget.value)}
                    />

                    <Group justify="flex-end">
                      <Button
                        color="red"
                        loading={reviewAction === "reject"}
                        variant="subtle"
                        onClick={() => void handleReview("reject")}
                      >
                        Reject
                      </Button>
                      <Button
                        loading={reviewAction === "verify"}
                        onClick={() => void handleReview("verify")}
                      >
                        Verify
                      </Button>
                    </Group>
                  </>
                ) : (
                  <Text c="dimmed">Choose a correction to inspect and review it.</Text>
                )}
              </Stack>
            </Card>
          </SimpleGrid>
        </Tabs.Panel>
      </Tabs>
    </Stack>
  );
}
