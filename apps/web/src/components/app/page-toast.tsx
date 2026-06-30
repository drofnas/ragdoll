import type { ComponentProps, RefObject } from "react";
import { useEffect, useRef, useState } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { cn } from "@/lib/utils";

export interface PageToastState {
  description: string;
  id: number;
  title: string;
  variant: NonNullable<ComponentProps<typeof Alert>["variant"]>;
  visible: boolean;
}

interface PageToastFrame {
  left: number;
  width: number;
}

export interface ShowPageToastOptions {
  description: string;
  title: string;
  variant: PageToastState["variant"];
}

export interface UsePageToastResult {
  showToast: (options: ShowPageToastOptions) => void;
  toast: PageToastState | null;
}

const PAGE_TOAST_DISMISS_MS = 10_000;
const PAGE_TOAST_FADE_MS = 300;

const PAGE_TOAST_SURFACE_STYLES: Record<
  PageToastState["variant"],
  { backgroundColor: string; borderColor: string } | undefined
> = {
  default: undefined,
  destructive: {
    backgroundColor:
      "color-mix(in hsl, hsl(var(--destructive)) 10%, hsl(var(--background)))",
    borderColor:
      "color-mix(in hsl, hsl(var(--destructive)) 25%, hsl(var(--background)))"
  },
  info: {
    backgroundColor:
      "color-mix(in hsl, hsl(var(--accent)) 40%, hsl(var(--background)))",
    borderColor:
      "color-mix(in hsl, hsl(var(--accent-foreground)) 15%, hsl(var(--background)))"
  },
  success: {
    backgroundColor:
      "color-mix(in hsl, hsl(var(--primary)) 10%, hsl(var(--background)))",
    borderColor:
      "color-mix(in hsl, hsl(var(--primary)) 20%, hsl(var(--background)))"
  }
};

export function usePageToast(): UsePageToastResult {
  const [toast, setToast] = useState<PageToastState | null>(null);
  const dismissTimeoutRef = useRef<number | null>(null);
  const removeTimeoutRef = useRef<number | null>(null);

  function clearToastTimers() {
    if (dismissTimeoutRef.current !== null) {
      window.clearTimeout(dismissTimeoutRef.current);
      dismissTimeoutRef.current = null;
    }
    if (removeTimeoutRef.current !== null) {
      window.clearTimeout(removeTimeoutRef.current);
      removeTimeoutRef.current = null;
    }
  }

  function showToast({ description, title, variant }: ShowPageToastOptions) {
    clearToastTimers();
    setToast({
      description,
      id: Date.now(),
      title,
      variant,
      visible: true
    });
  }

  useEffect(() => {
    if (!toast) {
      clearToastTimers();
      return;
    }

    const toastId = toast.id;
    dismissTimeoutRef.current = window.setTimeout(() => {
      setToast((current) =>
        current && current.id === toastId ? { ...current, visible: false } : current
      );
    }, PAGE_TOAST_DISMISS_MS);
    removeTimeoutRef.current = window.setTimeout(() => {
      setToast((current) => (current && current.id === toastId ? null : current));
    }, PAGE_TOAST_DISMISS_MS + PAGE_TOAST_FADE_MS);

    return clearToastTimers;
  }, [toast?.id]);

  useEffect(() => clearToastTimers, []);

  return {
    showToast,
    toast
  };
}

export function PageToast({
  contentRef,
  testIdPrefix = "page-toast",
  toast
}: {
  contentRef: RefObject<HTMLElement | null>;
  testIdPrefix?: string;
  toast: PageToastState | null;
}) {
  const [frame, setFrame] = useState<PageToastFrame | null>(null);

  useEffect(() => {
    const element = contentRef.current;
    if (!element) {
      return;
    }

    function updateFrame() {
      const rect = element.getBoundingClientRect();
      setFrame({
        left: rect.left + 16,
        width: Math.max(rect.width - 32, 0)
      });
    }

    updateFrame();
    const resizeObserver = new ResizeObserver(updateFrame);
    resizeObserver.observe(element);
    window.addEventListener("resize", updateFrame);

    return () => {
      resizeObserver.disconnect();
      window.removeEventListener("resize", updateFrame);
    };
  }, [contentRef]);

  if (!toast) {
    return null;
  }

  return (
    <div
      className="pointer-events-none fixed bottom-[10px] z-50"
      data-testid={`${testIdPrefix}-shell`}
      style={
        frame
          ? {
              left: `${frame.left}px`,
              width: `${frame.width}px`
            }
          : {
              left: "16px",
              right: "16px"
            }
      }
    >
      <Alert
        className={cn(
          "shadow-lg transition-opacity duration-300 ease-out",
          toast.visible ? "opacity-100" : "opacity-0"
        )}
        data-testid={testIdPrefix}
        style={PAGE_TOAST_SURFACE_STYLES[toast.variant]}
        variant={toast.variant}
      >
        <AlertTitle>{toast.title}</AlertTitle>
        <AlertDescription>{toast.description}</AlertDescription>
      </Alert>
    </div>
  );
}
