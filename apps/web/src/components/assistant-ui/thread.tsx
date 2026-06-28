import {
  ActionBarPrimitive,
  AuiIf,
  type AssistantState,
  ComposerPrimitive,
  MessagePrimitive,
  ThreadPrimitive,
  useAuiState
} from "@assistant-ui/react";
import { MarkdownTextPrimitive } from "@assistant-ui/react-markdown";
import { ArrowDown, ArrowUp, Check, Copy } from "lucide-react";
import {
  createContext,
  useContext,
  type ComponentType,
  type FC,
  type PropsWithChildren
} from "react";
import remarkGfm from "remark-gfm";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export type ThreadComponents = {
  AssistantMessage?: ComponentType | undefined;
  Welcome?: ComponentType | undefined;
};

export type ThreadProps = PropsWithChildren<{
  className?: string | undefined;
  components?: ThreadComponents | undefined;
  placeholder?: string | undefined;
}>;

const EMPTY_COMPONENTS: ThreadComponents = {};
const ThreadComponentsContext = createContext<ThreadComponents>(EMPTY_COMPONENTS);
const ThreadPlaceholderContext = createContext("Ask a question grounded in your uploaded material");

function isEmptyThread(s: AssistantState) {
  return s.thread.messages.length === 0 && !s.thread.isLoading;
}

export function Thread({
  children,
  className,
  components = EMPTY_COMPONENTS,
  placeholder
}: ThreadProps) {
  const isEmpty = useAuiState(isEmptyThread);

  return (
    <ThreadComponentsContext.Provider value={components}>
      <ThreadPlaceholderContext.Provider
        value={placeholder ?? "Ask a question grounded in your uploaded material"}
      >
        <ThreadPrimitive.Root
          className={cn("flex h-full min-h-0 flex-col bg-background", className)}
          data-empty={isEmpty}
        >
          <ThreadPrimitive.Viewport
            className="relative flex min-h-0 flex-1 flex-col overflow-y-auto scroll-smooth"
            turnAnchor="top"
          >
            <div
              className={cn(
                "mx-auto flex w-full max-w-3xl flex-1 flex-col px-4 pt-4 sm:px-6",
                isEmpty && "justify-center"
              )}
            >
              <AuiIf condition={isEmptyThread}>
                <ThreadWelcome />
              </AuiIf>

              <div className="mb-6 flex flex-col gap-4 empty:hidden">
                <ThreadPrimitive.Messages>{() => <ThreadMessage />}</ThreadPrimitive.Messages>
              </div>

              {children}

              <ThreadPrimitive.ViewportFooter className="sticky bottom-0 mt-auto bg-background/95 pb-4 pt-3 backdrop-blur supports-[backdrop-filter]:bg-background/80">
                <AuiIf condition={(s) => s.thread.isRunning}>
                  <div
                    className="mb-3 rounded-md border bg-muted/40 px-3 py-2 text-sm text-muted-foreground"
                    role="status"
                  >
                    Assistant is thinking...
                  </div>
                </AuiIf>
                <ThreadScrollToBottom />
                <Composer />
              </ThreadPrimitive.ViewportFooter>
            </div>
          </ThreadPrimitive.Viewport>
        </ThreadPrimitive.Root>
      </ThreadPlaceholderContext.Provider>
    </ThreadComponentsContext.Provider>
  );
}

function ThreadMessage() {
  const { AssistantMessage = AssistantMessageDefault } = useContext(ThreadComponentsContext);
  const role = useAuiState((s) => s.message.role);

  if (role === "user") {
    return <UserMessage />;
  }

  return <AssistantMessage />;
}

function ThreadWelcome() {
  const { Welcome = ThreadWelcomeDefault } = useContext(ThreadComponentsContext);

  return <Welcome />;
}

function ThreadWelcomeDefault() {
  return (
    <div className="mb-6 space-y-2 px-4 text-center">
      <h2 className="text-xl font-semibold tracking-normal text-foreground">
        Start a retrieval chat
      </h2>
      <p className="text-sm text-muted-foreground">
        Ask anything grounded in the documents available to this session.
      </p>
    </div>
  );
}

function ThreadScrollToBottom() {
  return (
    <ThreadPrimitive.ScrollToBottom asChild>
      <Button
        aria-label="Scroll to bottom"
        className="absolute -top-9 left-1/2 h-8 w-8 -translate-x-1/2 rounded-full disabled:invisible"
        size="icon"
        type="button"
        variant="outline"
      >
        <ArrowDown className="h-4 w-4" />
      </Button>
    </ThreadPrimitive.ScrollToBottom>
  );
}

function Composer() {
  const placeholder = useContext(ThreadPlaceholderContext);

  return (
    <ComposerPrimitive.Root className="rounded-md border bg-background p-2 shadow-sm focus-within:ring-2 focus-within:ring-ring">
      <ComposerPrimitive.Input
        aria-label="Message"
        autoFocus
        className="max-h-36 min-h-20 w-full resize-none bg-transparent px-2 py-1 text-sm leading-6 outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed"
        placeholder={placeholder}
        rows={3}
      />
      <div className="flex items-center justify-end">
        <AuiIf condition={(s) => !s.thread.isRunning}>
          <ComposerPrimitive.Send asChild>
            <Button aria-label="Send message" size="sm" type="submit">
              <ArrowUp className="h-4 w-4" />
              Send
            </Button>
          </ComposerPrimitive.Send>
        </AuiIf>
        <AuiIf condition={(s) => s.thread.isRunning}>
          <Button aria-label="Assistant thinking" disabled size="sm" type="button">
            Thinking
          </Button>
        </AuiIf>
      </div>
    </ComposerPrimitive.Root>
  );
}

function UserMessage() {
  return (
    <MessagePrimitive.Root className="flex justify-end" data-role="user">
      <div className="max-w-[82%] rounded-md bg-primary px-4 py-3 text-sm leading-6 text-primary-foreground">
        <MessagePrimitive.Parts />
      </div>
    </MessagePrimitive.Root>
  );
}

function AssistantMessageDefault() {
  return (
    <MessagePrimitive.Root className="space-y-3" data-role="assistant">
      <div className="rounded-md border bg-background p-4 text-sm leading-7 shadow-sm">
        <ThreadMessageContent />
      </div>
      <AssistantMessageActions />
    </MessagePrimitive.Root>
  );
}

function MarkdownMessageText() {
  return (
    <MarkdownTextPrimitive
      className="space-y-3 break-words text-sm leading-7 text-foreground [&_a]:font-medium [&_a]:text-primary [&_a]:underline [&_code]:rounded [&_code]:bg-muted [&_code]:px-1 [&_code]:py-0.5 [&_ol]:ml-5 [&_ol]:list-decimal [&_pre]:overflow-x-auto [&_pre]:rounded-md [&_pre]:bg-muted [&_pre]:p-3 [&_ul]:ml-5 [&_ul]:list-disc"
      remarkPlugins={[remarkGfm]}
    />
  );
}

export function ThreadMessageContent() {
  return <MessagePrimitive.Parts components={{ Text: MarkdownMessageText }} />;
}

export function AssistantMessageActions({ className }: { className?: string | undefined }) {
  return (
    <ActionBarPrimitive.Root
      autohide="not-last"
      className={cn("flex items-center gap-1 text-muted-foreground", className)}
      hideWhenRunning
    >
      <ActionBarPrimitive.Copy asChild>
        <Button aria-label="Copy message" size="sm" type="button" variant="ghost">
          <AuiIf condition={(s) => s.message.isCopied}>
            <Check className="h-4 w-4" />
          </AuiIf>
          <AuiIf condition={(s) => !s.message.isCopied}>
            <Copy className="h-4 w-4" />
          </AuiIf>
          Copy
        </Button>
      </ActionBarPrimitive.Copy>
    </ActionBarPrimitive.Root>
  );
}
