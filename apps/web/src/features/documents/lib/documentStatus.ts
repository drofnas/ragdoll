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

function clampProgress(value: number) {
  return Math.min(100, Math.max(0, value));
}

function progressPercent(indexedChunkCount: number, chunkCount: number) {
  if (chunkCount <= 0) {
    return 0;
  }

  return clampProgress((indexedChunkCount / chunkCount) * 100);
}

function percentLabel(value: number) {
  return `${clampProgress(Math.round(value))}%`;
}

function overallStageProgress(stage: OrderedStage, stageProgressPercent: number) {
  const stageIndex = ORDERED_STAGES.indexOf(stage);
  const normalizedStageProgress = clampProgress(stageProgressPercent) / 100;
  const overallProgress = ((stageIndex + normalizedStageProgress) / ORDERED_STAGES.length) * 100;
  return clampProgress(Math.round(stage === "graph" ? Math.min(overallProgress, 99) : overallProgress));
}

function processingChunkCount(source: DocumentStatusSource, indexedChunkCount: number) {
  if ((source.queue_runtime?.status === "queued") || source.processing_status.parsing === "processing") {
    return 0;
  }

  if (source.queue_runtime?.chunk_progress_total && source.queue_runtime.chunk_progress_total > 0) {
    return source.queue_runtime.chunk_progress_current;
  }

  return indexedChunkCount;
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
  const chunkCount = source.chunk_count ?? 0;
  const indexedChunkCount = source.indexed_chunk_count ?? 0;
  const runtime = source.queue_runtime;
  const runtimeTotal = runtime?.chunk_progress_total ?? 0;
  const displayChunkTotal = runtimeTotal > 0 ? runtimeTotal : chunkCount;

  if (runtime?.status === "queued") {
    return {
      label: runtime.queue_position ? `Queued (#${runtime.queue_position})` : "Queued",
      progressTone: "idle" satisfies ChunkProgressTone,
      progressValue: 0,
      valueLabel: percentLabel(0)
    };
  }

  if (runtime?.status === "started" || source.active_job?.status === "processing" || overall === "processing") {
    const currentStage = resolveProcessingStage(source);
    if (currentStage === "graph") {
      const stageProgress = displayChunkTotal > 0 ? 100 : 90;
      const progressValue = overallStageProgress(currentStage, stageProgress);
      return {
        label: labelForStage(currentStage) ?? "Processing",
        progressTone: "processing" satisfies ChunkProgressTone,
        progressValue,
        valueLabel: percentLabel(progressValue)
      };
    }

    const currentChunkCount = processingChunkCount(source, indexedChunkCount);
    const label = labelForStage(currentStage) ?? "Processing";
    const stageProgress = progressPercent(currentChunkCount, displayChunkTotal);
    const progressValue = currentStage ? overallStageProgress(currentStage, stageProgress) : stageProgress;
    return {
      label,
      progressTone: "processing" satisfies ChunkProgressTone,
      progressValue,
      valueLabel: displayChunkTotal > 0 ? percentLabel(progressValue) : "Starting"
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
    const failedStage =
      findStageWithValue(source.processing_status, "failed") ??
      findStageWithValue(source.processing_status, "processing") ??
      nextIncompleteStage(source);
    const stageProgress = progressPercent(processingChunkCount(source, indexedChunkCount), displayChunkTotal);
    const progressValue = failedStage ? overallStageProgress(failedStage, stageProgress) : stageProgress;
    return {
      label: "Failed",
      progressTone: "failed" satisfies ChunkProgressTone,
      progressValue,
      valueLabel: percentLabel(progressValue)
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
    progressValue: displayChunkTotal > 0 ? 100 : 0,
    valueLabel: String(displayChunkTotal)
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
