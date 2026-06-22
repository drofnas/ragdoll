import type { ProcessingStageStatus } from "@contracts";

const fileSizeFormatter = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 1
});

export function formatDateTime(value: string | null | undefined) {
  if (!value) {
    return "Not available";
  }

  return new Date(value).toLocaleString();
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
