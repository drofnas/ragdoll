import { AlertCircle, CheckCircle2, FileText, Upload, X } from "lucide-react";
import { useRef, useState, type ChangeEvent, type DragEvent } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { formatFileSize } from "@/shared/lib/formatting";

export interface DocumentUploadQueueItem {
  errorMessage?: string;
  file: File;
  id: string;
  spaceId: string;
  status: "queued" | "uploading" | "completed" | "failed";
}

interface DocumentUploadDropzoneProps {
  disabled?: boolean;
  disabledCopy?: string;
  isUploading?: boolean;
  items: DocumentUploadQueueItem[];
  onFilesSelected: (files: File[]) => void;
  onRemoveItem: (itemId: string) => void;
  targetLabel: string;
}

function renderQueueBadge(status: DocumentUploadQueueItem["status"]) {
  if (status === "uploading") {
    return <Badge variant="outline" className="border-sky-200 bg-sky-50 text-sky-700">Uploading</Badge>;
  }

  if (status === "completed") {
    return <Badge variant="outline" className="border-transparent bg-primary/10 text-primary">Added</Badge>;
  }

  if (status === "failed") {
    return <Badge variant="outline" className="border-transparent bg-destructive/10 text-destructive">Failed</Badge>;
  }

  return <Badge variant="outline" className="border-amber-200 bg-amber-50 text-amber-700">Queued</Badge>;
}

export function DocumentUploadDropzone({
  disabled,
  disabledCopy,
  isUploading,
  items,
  onFilesSelected,
  onRemoveItem,
  targetLabel
}: DocumentUploadDropzoneProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  function handleFiles(files: File[]) {
    if (disabled || files.length === 0) {
      return;
    }

    onFilesSelected(files);
  }

  function handleInputChange(event: ChangeEvent<HTMLInputElement>) {
    handleFiles(Array.from(event.currentTarget.files ?? []));
    event.currentTarget.value = "";
  }

  function handleDragOver(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    if (!disabled) {
      setIsDragging(true);
    }
  }

  function handleDragLeave(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(false);
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(false);
    handleFiles(Array.from(event.dataTransfer.files));
  }

  return (
    <div className="space-y-4">
      <input
        ref={inputRef}
        aria-label="Upload documents"
        accept=".pdf,.docx,.txt,.md,.markdown"
        className="sr-only"
        disabled={disabled}
        multiple
        type="file"
        onChange={handleInputChange}
      />

      <div
        className={cn(
          "rounded-xl border border-dashed px-6 py-8 transition-colors",
          disabled
            ? "border-border bg-muted/20"
            : isDragging
              ? "border-primary bg-primary/5"
              : "border-border bg-muted/10 hover:border-primary/40 hover:bg-primary/5"
        )}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        <div className="flex flex-col items-center gap-4 text-center">
          <div className="rounded-full border bg-background p-3">
            <Upload className="h-5 w-5" />
          </div>
          <div className="space-y-1">
            <p className="text-base font-semibold">Drag and drop documents here</p>
            <p className="text-sm text-muted-foreground">
              Drop multiple files or choose them from your computer.
            </p>
          </div>
          <div className="flex flex-wrap items-center justify-center gap-3">
            <Button disabled={disabled} type="button" onClick={() => inputRef.current?.click()}>
              Choose files
            </Button>
            <span className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
              PDF, DOCX, Markdown, TXT
            </span>
          </div>
          <div className="text-sm text-muted-foreground">
            <span className="font-medium text-foreground">Target Space:</span> {targetLabel}
          </div>
          {disabled && disabledCopy ? (
            <p className="max-w-lg text-sm text-muted-foreground">{disabledCopy}</p>
          ) : null}
        </div>
      </div>

      {items.length > 0 ? (
        <div className="space-y-2">
          {items.map((item) => (
            <div
              key={item.id}
              className="flex items-start justify-between gap-3 rounded-lg border bg-background px-4 py-3"
            >
              <div className="flex min-w-0 gap-3">
                <div className="rounded-md bg-muted/40 p-2">
                  {item.status === "completed" ? (
                    <CheckCircle2 className="h-4 w-4 text-primary" />
                  ) : item.status === "failed" ? (
                    <AlertCircle className="h-4 w-4 text-destructive" />
                  ) : (
                    <FileText className="h-4 w-4 text-muted-foreground" />
                  )}
                </div>
                <div className="min-w-0 space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="truncate text-sm font-medium">{item.file.name}</p>
                    {renderQueueBadge(item.status)}
                    <Badge variant="outline">{formatFileSize(item.file.size)}</Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {item.status === "uploading"
                      ? "Adding document to the library…"
                      : item.status === "completed"
                        ? "Document added to the library."
                        : item.status === "failed"
                          ? item.errorMessage ?? "Unable to add this document right now."
                          : "Waiting to upload…"}
                  </p>
                </div>
              </div>
              <Button
                aria-label={`Remove ${item.file.name}`}
                disabled={item.status === "uploading" || Boolean(isUploading && item.status === "queued")}
                size="icon"
                type="button"
                variant="ghost"
                onClick={() => onRemoveItem(item.id)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
