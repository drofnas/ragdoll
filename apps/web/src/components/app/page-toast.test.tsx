import { act, fireEvent, render, screen } from "@testing-library/react";
import { useRef } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PageToast, usePageToast } from "./page-toast";

function PageToastHarness() {
  const contentRef = useRef<HTMLDivElement | null>(null);
  const { showToast, toast } = usePageToast();

  return (
    <div>
      <div ref={contentRef} data-testid="page-toast-content" />
      <button
        type="button"
        onClick={() =>
          showToast({
            description: "Toast description one.",
            title: "Saved",
            variant: "success"
          })
        }
      >
        Show first toast
      </button>
      <button
        type="button"
        onClick={() =>
          showToast({
            description: "Toast description two.",
            title: "Replaced",
            variant: "destructive"
          })
        }
      >
        Show second toast
      </button>
      <PageToast contentRef={contentRef} toast={toast} />
    </div>
  );
}

describe("PageToast", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("renders a fixed shell when a toast is active", async () => {
    render(<PageToastHarness />);

    fireEvent.click(screen.getByRole("button", { name: "Show first toast" }));

    const toast = await screen.findByTestId("page-toast");
    expect(toast).toHaveTextContent("Saved");
    expect(toast).toHaveTextContent("Toast description one.");
    expect(screen.getByTestId("page-toast-shell")).toHaveClass("fixed");
  });

  it("fades after 10 seconds and removes after the fade duration", async () => {
    vi.useFakeTimers();
    render(<PageToastHarness />);

    fireEvent.click(screen.getByRole("button", { name: "Show first toast" }));

    expect(screen.getByTestId("page-toast")).toHaveClass("opacity-100");

    await act(async () => {
      vi.advanceTimersByTime(10_000);
    });

    expect(screen.getByTestId("page-toast")).toHaveClass("opacity-0");

    await act(async () => {
      vi.advanceTimersByTime(301);
    });

    expect(screen.queryByTestId("page-toast")).not.toBeInTheDocument();
  });

  it("replaces the current toast and resets the dismissal timer", async () => {
    vi.useFakeTimers();
    render(<PageToastHarness />);

    fireEvent.click(screen.getByRole("button", { name: "Show first toast" }));
    expect(screen.getByTestId("page-toast")).toHaveTextContent("Toast description one.");

    await act(async () => {
      vi.advanceTimersByTime(9_000);
    });

    fireEvent.click(screen.getByRole("button", { name: "Show second toast" }));

    const replacedToast = screen.getByTestId("page-toast");
    expect(replacedToast).toHaveTextContent("Replaced");
    expect(replacedToast).toHaveTextContent("Toast description two.");

    await act(async () => {
      vi.advanceTimersByTime(2_000);
    });

    expect(screen.getByTestId("page-toast")).toHaveClass("opacity-100");

    await act(async () => {
      vi.advanceTimersByTime(8_000);
    });

    expect(screen.getByTestId("page-toast")).toHaveClass("opacity-0");
  });

  it("cleans up pending timers on unmount", async () => {
    vi.useFakeTimers();
    const { unmount } = render(<PageToastHarness />);

    fireEvent.click(screen.getByRole("button", { name: "Show first toast" }));
    expect(screen.getByTestId("page-toast")).toBeInTheDocument();

    unmount();

    await act(async () => {
      expect(() => vi.runOnlyPendingTimers()).not.toThrow();
    });
  });
});
