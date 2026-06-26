import type {
  DocumentProcessingJobResponse,
  DocumentProcessingStatusResponse,
  ProcessingStageStatus,
  ProcessingStatus
} from "@contracts";

const TERMINAL_STATUSES: ProcessingStageStatus[] = ["completed", "deferred", "failed"];
const ORDERED_STAGES = ["parsing", "vector", "extraction", "graph"] as const;

type OrderedStage = (typeof ORDERED_STAGES)[number];

interface DocumentStatusSource {
  active_job?: DocumentProcessingJobResponse | null;
  has_queued_reprocess?: boolean;
  processing_status: ProcessingStatus;
  queued_job_count?: number;
}

const STAGE_LABELS: Record<OrderedStage, string> = {
  extraction: "Extracting",
  graph: "Graphing",
  parsing: "Parsing",
  vector: "Vectorizing"
};

function findStageWithValue(
  processingStatus: ProcessingStatus,
  expectedValue: ProcessingStageStatus
): OrderedStage | null {
  for (const stage of ORDERED_STAGES) {
    if (processingStatus[stage] === expectedValue) {
      return stage;
    }
  }

  return null;
}

function labelForStage(stage: OrderedStage | null) {
  return stage ? STAGE_LABELS[stage] : null;
}

export function hasInFlightDocumentWork(source: DocumentStatusSource) {
  const overall = source.processing_status.overall;
  return Boolean(
    source.active_job ||
      (source.queued_job_count ?? 0) > 0 ||
      (overall && !TERMINAL_STATUSES.includes(overall))
  );
}

export function hasQueuedDocumentReprocess(source: DocumentStatusSource) {
  return Boolean(source.has_queued_reprocess || (source.queued_job_count ?? 0) > 0);
}

export function getDocumentStatusPresentation(source: DocumentStatusSource) {
  const overall = source.processing_status.overall ?? "pending";
  const queuedJobCount = source.queued_job_count ?? 0;

  if (source.active_job?.status === "processing" || overall === "processing") {
    return {
      badgeValue: "processing",
      label: labelForStage(findStageWithValue(source.processing_status, "processing")) ?? "Processing"
    };
  }

  if (queuedJobCount > 0 || overall === "pending") {
    return {
      badgeValue: "pending",
      label: "Queued"
    };
  }

  if (overall === "failed") {
    return {
      badgeValue: "failed",
      label: "Failed"
    };
  }

  if (overall === "deferred") {
    return {
      badgeValue: "deferred",
      label: "Deferred"
    };
  }

  return {
    badgeValue: "completed",
    label: "Completed"
  };
}

export function isRefreshLocked(source: DocumentStatusSource) {
  return hasInFlightDocumentWork(source);
}

export function buildStatusMap(
  statuses: DocumentProcessingStatusResponse[] | undefined
) {
  return new Map(statuses?.map((status) => [status.document_id, status]) ?? []);
}
