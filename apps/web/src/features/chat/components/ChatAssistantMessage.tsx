import type { ChatMessageRecord, Citation } from "@contracts";
import { MessagePrimitive, useAuiState } from "@assistant-ui/react";
import { Link } from "react-router-dom";

import {
  AssistantMessageActions,
  ThreadMessageContent
} from "@/components/assistant-ui/thread";
import { StatusBadge } from "@/components/app/status-badge";
import { Button } from "@/components/ui/button";
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger
} from "@/components/ui/hover-card";
import { formatDateTime } from "@/shared/lib/formatting";

type ChatAssistantMessageProps = {
  messageById: ReadonlyMap<string, ChatMessageRecord>;
  onOpenCorrection: (message: ChatMessageRecord) => void;
};

function formatDocumentCitationLabel(citation: Citation) {
  const title = citation.title?.trim() || "Document";
  const line = citation.line_number ? `line ${citation.line_number}` : "line unavailable";
  return `${title} (${line})`;
}

function DocumentCitationsHoverCard({
  citations,
  messageId
}: {
  citations: Citation[];
  messageId: string;
}) {
  return (
    <HoverCard openDelay={0}>
      <HoverCardTrigger asChild>
        <Button className="h-8 px-2.5" size="sm" type="button" variant="outline">
          Citations
        </Button>
      </HoverCardTrigger>
      <HoverCardContent align="start" className="w-80 p-3">
        <div className="space-y-1">
          {citations.map((citation, index) => (
            <Link
              className="block rounded-md px-2 py-1.5 text-sm text-foreground transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              key={`${messageId}-${citation.document_id}-${index}`}
              to={`/documents/${citation.document_id}`}
            >
              {formatDocumentCitationLabel(citation)}
            </Link>
          ))}
        </div>
      </HoverCardContent>
    </HoverCard>
  );
}

export function ChatAssistantMessage({
  messageById,
  onOpenCorrection
}: ChatAssistantMessageProps) {
  const messageId = useAuiState((s) => s.message.id);
  const messageRecord = messageById.get(messageId);
  const documentCitations =
    messageRecord?.citations?.filter((citation) => citation.document_id) ?? [];

  return (
    <MessagePrimitive.Root className="rounded-md border bg-background p-4 shadow-sm" data-role="assistant">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge label="assistant" value="active" />
          {messageRecord?.degraded ? (
            <StatusBadge label="degraded" value="degraded" />
          ) : null}
        </div>
        {messageRecord ? (
          <p className="text-sm text-muted-foreground">
            {formatDateTime(messageRecord.created_at)}
          </p>
        ) : null}
      </div>

      <div className="mt-4">
        <ThreadMessageContent />
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        {documentCitations.length > 0 && messageRecord ? (
          <DocumentCitationsHoverCard
            citations={documentCitations}
            messageId={messageRecord.id}
          />
        ) : null}
        {messageRecord ? (
          <Button
            size="sm"
            type="button"
            variant="ghost"
            onClick={() => onOpenCorrection(messageRecord)}
          >
            Submit correction
          </Button>
        ) : null}
        <AssistantMessageActions />
      </div>
    </MessagePrimitive.Root>
  );
}
