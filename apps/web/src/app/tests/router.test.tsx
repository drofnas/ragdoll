import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";

import { AppProviders } from "../providers";
import { AppRouter } from "../router";

function renderRoute(path: string, scaffoldMode?: "anonymous" | "user" | "admin") {
  globalThis.__RAGDOLL_SCAFFOLD_AUTH_MODE__ = scaffoldMode;
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppProviders>
        <AppRouter />
      </AppProviders>
    </MemoryRouter>
  );
}

describe("AppRouter", () => {
  beforeEach(() => {
    globalThis.__RAGDOLL_SCAFFOLD_AUTH_MODE__ = undefined;
  });

  it("renders public home route", () => {
    renderRoute("/");
    expect(screen.getByText("Ragdoll Clean-Room Rebuild")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Status" })).toHaveAttribute(
      "href",
      "http://localhost:8031/status"
    );
  });

  it("renders protected dashboard for scaffold user mode", () => {
    renderRoute("/dashboard", "user");
    expect(screen.getByText("Authenticated Dashboard Placeholder")).toBeInTheDocument();
  });

  it("renders admin placeholder for scaffold admin mode", () => {
    renderRoute("/admin", "admin");
    expect(screen.getByText("Admin Placeholder")).toBeInTheDocument();
  });
});
