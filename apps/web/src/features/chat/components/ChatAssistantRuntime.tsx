import type { ChatMessageRecord } from "@contracts";
import {
  AssistantRuntimeProvider,
  useExternalStoreRuntime,
  type AppendMessage,
  type ThreadMessageLike
} from "@assistant-ui/react";
import { useMemo, type PropsWithChildren } from "react";

type ChatAssistantRuntimeProps = PropsWithChildren<{
  isLoading?: boolean | undefined;
  isRunning?: boolean | undefined;
  isSendDisabled?: boolean | undefined;
  messages: readonly ChatMessageRecord[];
  onNew: (message: AppendMessage) => Promise<void>;
}>;

function normalizeRole(role: string): ThreadMessageLike["role"] {
  if (role === "assistant" || role === "system") {
    return role;
  }

  return "user";
}

export function convertChatMessageToThreadMessage(
  message: ChatMessageRecord
): ThreadMessageLike {
  return {
    content: [{ type: "text", text: message.content }],
    createdAt: new Date(message.created_at),
    id: message.id,
    metadata: {
      custom: {
        ragdollMessageId: message.id
      }
    },
    role: normalizeRole(message.role)
  };
}

export function extractAppendMessageText(message: AppendMessage) {
  if (typeof message.content === "string") {
    return message.content.trim();
  }

  return message.content
    .map((part) => {
      if ("text" in part && typeof part.text === "string") {
        return part.text;
      }

      return "";
    })
    .join("\n")
    .trim();
}

export function ChatAssistantRuntime({
  children,
  isLoading = false,
  isRunning = false,
  isSendDisabled = false,
  messages,
  onNew
}: ChatAssistantRuntimeProps) {
  const adapter = useMemo(
    () => ({
      convertMessage: convertChatMessageToThreadMessage,
      isLoading,
      isRunning,
      isSendDisabled,
      messages,
      onNew,
      unstable_capabilities: {
        copy: true
      }
    }),
    [isLoading, isRunning, isSendDisabled, messages, onNew]
  );
  const runtime = useExternalStoreRuntime<ChatMessageRecord>(adapter);

  return <AssistantRuntimeProvider runtime={runtime}>{children}</AssistantRuntimeProvider>;
}
