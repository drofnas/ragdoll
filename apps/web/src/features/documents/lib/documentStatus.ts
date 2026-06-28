import type {
  DocumentProcessingJobResponse,
  DocumentQueueRuntimeResponse,
  DocumentProcessingStatusResponse,
  ProcessingStageStatus,
  ProcessingStatus
} from "@contracts";

const TERMINAL_STATUSES: ProcessingStageStatus[] = ["completed", "deferred", "failed"];
const ORDERED_STAGES = ["parsing", "vector", "extraction", "graph"] as const;

type OrderedStage = (typeof ORDERED_STAGES)[number];

interface DocumentStatusSource {
  active_job?: DocumentProcessingJobResponse | null;
  chunk_count?: number;
  has_queued_reprocess?: boolean;
  indexed_chunk_count?: number;
  latest_job?: DocumentProcessingJobResponse | null;
  processing_status: ProcessingStatus;
  queue_runtime?: DocumentQueueRuntimeResponse | null;
  queued_job_count?: number;
}

type ChunkProgressTone = "completed" | "failed" | "idle" | "processing";

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

function isOrderedStage(value: string | null | undefined): value is OrderedStage {
  return Boolean(value && ORDERED_STAGES.includes(value as OrderedStage));
}

function stageRank(stage: OrderedStage | null) {
  return stage ? ORDERED_STAGES.indexOf(stage) : -1;
}

function nextIncompleteStage(source: DocumentStatusSource): OrderedStage | null {
  for (const stage of ORDERED_STAGES) {
    if (source.processing_status[stage] !== "completed") {
      return stage;
    }
  }

  return null;
}

function resolveProcessingStage(source: DocumentStatusSource): OrderedStage | null {
  const runtimeStage = isOrderedStage(source.queue_runtime?.stage) ? source.queue_runtime.stage : null;
  const processingStage = findStageWithValue(source.processing_status, "processing");
  if (processingStage && runtimeStage) {
    return stageRank(processingStage) >= stageRank(runtimeStage) ? processingStage : runtimeStage;
  }
  if (processingStage) {
    return processingStage;
  }

  if (source.processing_status.overall === "processing") {
    const pendingStage = nextIncompleteStage(source);
    if (pendingStage) {
      return pendingStage;
    }
  }

  if (runtimeStage) {
    return runtimeStage;
  }

  const requestedStage = source.active_job?.requested_stage;
  return isOrderedStage(requestedStage) ? requestedStage : null;
}

function resolveWorkflowStartStage(source: DocumentStatusSource): OrderedStage | null {
  const requestedStage = source.active_job?.requested_stage ?? source.latest_job?.requested_stage;
  if (isOrderedStage(requestedStage)) {
    return requestedStage;
  }

  const activeStage =
    findStageWithValue(source.processing_status, "processing") ??
    findStageWithValue(source.processing_status, "failed") ??
    nextIncompleteStage(source);
  return activeStage;
}

function clampProgress(value: number) {
  return Math.min(100, Math.max(0, value));
}

function percentLabel(value: number) {
  return `${clampProgress(Math.round(value))}%`;
}

function resolveStageItemTotal(source: DocumentStatusSource) {
  const runtimeTotal = source.queue_runtime?.chunk_progress_total ?? 0;
  return Math.max(source.chunk_count ?? 0, source.indexed_chunk_count ?? 0, runtimeTotal);
}

function resolveCompletedChunkCount(source: DocumentStatusSource) {
  return Math.max(source.chunk_count ?? 0, source.indexed_chunk_count ?? 0);
}

function resolveWorkflowStages(source: DocumentStatusSource) {
  const startStage = resolveWorkflowStartStage(source);
  if (!startStage) {
    return [...ORDERED_STAGES];
  }

  return ORDERED_STAGES.slice(stageRank(startStage));
}

function resolveStageProgressCount(source: DocumentStatusSource, currentStage: OrderedStage | null) {
  if (!currentStage || source.queue_runtime?.status === "queued") {
    return 0;
  }

  const runtimeStage = isOrderedStage(source.queue_runtime?.stage) ? source.queue_runtime.stage : null;
  if (
    runtimeStage === currentStage &&
    source.queue_runtime?.chunk_progress_total &&
    source.queue_runtime.chunk_progress_total > 0
  ) {
    return source.queue_runtime.chunk_progress_current;
  }

  return 0;
}

function computeItemProgress(
  source: DocumentStatusSource,
  {
    currentStage,
    totalItemsPerStage
  }: {
    currentStage: OrderedStage | null;
    totalItemsPerStage: number;
  }
) {
  const workflowStages = resolveWorkflowStages(source);
  if (workflowStages.length === 0 || totalItemsPerStage <= 0) {
    return {
      processedItems: 0,
      totalItems: 0
    };
  }

  const totalItems = workflowStages.length * totalItemsPerStage;
  if (!currentStage) {
    const allCompleted = workflowStages.every((stage) => source.processing_status[stage] === "completed");
    return {
      processedItems: allCompleted ? totalItems : 0,
      totalItems
    };
  }

  const currentStageIndex = workflowStages.indexOf(currentStage);
  const completedStagesBeforeCurrent = currentStageIndex < 0 ? 0 : currentStageIndex;
  const processedItemsBeforeCurrent = completedStagesBeforeCurrent * totalItemsPerStage;
  const currentStageItems = Math.min(
    totalItemsPerStage,
    Math.max(0, resolveStageProgressCount(source, currentStage))
  );
  return {
    processedItems: Math.min(totalItems, processedItemsBeforeCurrent + currentStageItems),
    totalItems
  };
}

function computeProgressValue(
  processedItems: number,
  totalItems: number,
  { isTerminal }: { isTerminal: boolean }
) {
  if (totalItems <= 0) {
    return 0;
  }

  if (isTerminal && processedItems >= totalItems) {
    return 100;
  }

  const progressValue = clampProgress(Math.round((processedItems / totalItems) * 100));
  return !isTerminal && processedItems >= totalItems ? 99 : progressValue;
}

export function hasInFlightDocumentWork(source: DocumentStatusSource) {
  const overall = source.processing_status.overall;
  const queueStatus = source.queue_runtime?.status;
  return Boolean(
    source.active_job ||
      (queueStatus && !["failed", "finished"].includes(queueStatus)) ||
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
      label: labelForStage(resolveProcessingStage(source)) ?? "Processing"
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

export function getDocumentChunkStatusPresentation(source: DocumentStatusSource) {
  const overall = source.processing_status.overall ?? "pending";
  const queuedJobCount = source.queued_job_count ?? 0;
  const runtime = source.queue_runtime;
  const stageItemTotal = resolveStageItemTotal(source);
  const currentStage = resolveProcessingStage(source);

  if (runtime?.status === "queued") {
    return {
      label: runtime.queue_position ? `Queued (#${runtime.queue_position})` : "Queued",
      progressTone: "idle" satisfies ChunkProgressTone,
      progressValue: 0,
      valueLabel: percentLabel(0)
    };
  }

  if (runtime?.status === "started" || source.active_job?.status === "processing" || overall === "processing") {
    const { processedItems, totalItems } = computeItemProgress(source, {
      currentStage,
      totalItemsPerStage: stageItemTotal
    });
    const progressValue = computeProgressValue(processedItems, totalItems, { isTerminal: false });
    return {
      label: labelForStage(currentStage) ?? "Processing",
      progressTone: "processing" satisfies ChunkProgressTone,
      progressValue,
      valueLabel: totalItems > 0 ? percentLabel(progressValue) : "Starting"
    };
  }

  if (source.has_queued_reprocess || queuedJobCount > 0 || overall === "pending") {
    return {
      label: "Queued",
      progressTone: "idle" satisfies ChunkProgressTone,
      progressValue: 0,
      valueLabel: percentLabel(0)
    };
  }

  if (runtime?.status === "failed" || overall === "failed") {
    const currentStageForFailure =
      findStageWithValue(source.processing_status, "failed") ??
      findStageWithValue(source.processing_status, "processing") ??
      nextIncompleteStage(source);
    const { processedItems, totalItems } = computeItemProgress(source, {
      currentStage: currentStageForFailure,
      totalItemsPerStage: stageItemTotal
    });
    const progressValue = computeProgressValue(processedItems, totalItems, { isTerminal: false });
    return {
      label: "Failed",
      progressTone: "failed" satisfies ChunkProgressTone,
      progressValue,
      valueLabel: String(resolveCompletedChunkCount(source))
    };
  }

  if (overall === "deferred") {
    return {
      label: "Deferred",
      progressTone: "idle" satisfies ChunkProgressTone,
      progressValue: 0,
      valueLabel: percentLabel(0)
    };
  }

  return {
    label: "Completed",
    progressTone: "completed" satisfies ChunkProgressTone,
    progressValue: stageItemTotal > 0 ? 100 : 0,
    valueLabel: String(resolveCompletedChunkCount(source))
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
