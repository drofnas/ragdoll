import type { Citation, ProcessingStageStatus, SearchMode, SourceTier } from "@contracts";

const fileSizeFormatter = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 1
});

export function formatDateTime(value: string | null | undefined) {
  if (!value) {
    return "Not available";
  }

  return new Date(value).toLocaleString();
}

export function formatElapsedDuration(value: string | null | undefined, now = Date.now()) {
  if (!value) {
    return "Not available";
  }

  const startedAt = new Date(value).getTime();
  if (Number.isNaN(startedAt)) {
    return "Not available";
  }

  const elapsedMs = Math.max(0, now - startedAt);
  const totalSeconds = Math.floor(elapsedMs / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  if (minutes > 0) {
    return `${minutes}m ${seconds}s`;
  }
  return `${seconds}s`;
}

export function formatFileSize(bytes: number) {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${fileSizeFormatter.format(bytes / 1024)} KB`;
  }
  if (bytes < 1024 * 1024 * 1024) {
    return `${fileSizeFormatter.format(bytes / (1024 * 1024))} MB`;
  }
  return `${fileSizeFormatter.format(bytes / (1024 * 1024 * 1024))} GB`;
}

export function humanizeStageStatus(status: ProcessingStageStatus) {
  return status.replace(/_/g, " ");
}

export function humanizeLabel(value: string) {
  return value.replace(/_/g, " ");
}

export function formatSearchMode(mode: SearchMode) {
  return humanizeLabel(mode);
}

export function formatSourceTier(sourceTier: SourceTier | null | undefined) {
  if (!sourceTier) {
    return "unknown";
  }
  return humanizeLabel(sourceTier);
}

export function formatCitationLabel(citation: Citation) {
  if (citation.title && citation.locator) {
    return `${citation.title} (${citation.locator})`;
  }
  if (citation.title) {
    return citation.title;
  }
  if (citation.locator) {
    return citation.locator;
  }
  if (citation.entity_id) {
    return `Entity ${citation.entity_id}`;
  }
  if (citation.document_id) {
    return `Document ${citation.document_id}`;
  }
  return "Linked evidence";
}

export function formatScore(score: number) {
  return score.toFixed(2);
}
