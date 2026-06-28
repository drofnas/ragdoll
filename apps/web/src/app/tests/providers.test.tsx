import { render, screen } from "@testing-library/react";
import { useQueryClient } from "@tanstack/react-query";
import { afterEach, describe, expect, it } from "vitest";

import { AppProviders } from "../providers";
import { useAuthSession } from "../../shared/state/authSession";
import { useSpaceScope } from "../../shared/state/spaceScope";

function Consumer() {
  const queryClient = useQueryClient();
  const auth = useAuthSession();
  const scope = useSpaceScope();

  return (
    <div>
      <span>{queryClient ? "query-ready" : "query-missing"}</span>
      <span>{auth.status}</span>
      <span>{String(scope.allSpaces)}</span>
    </div>
  );
}

describe("AppProviders", () => {
  afterEach(() => {
    window.localStorage.clear();
  });

  it("mounts query, auth, and space scope providers", () => {
    render(
      <AppProviders>
        <Consumer />
      </AppProviders>
    );

    expect(screen.getByText("query-ready")).toBeInTheDocument();
    expect(screen.getByText("anonymous")).toBeInTheDocument();
    expect(screen.getByText("false")).toBeInTheDocument();
  });
});
