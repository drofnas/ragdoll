import type { SpaceResponse } from "@contracts";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppProviders } from "../../../app/providers";
import { AUTH_ACCESS_TOKEN_STORAGE_KEY } from "../../../shared/state/authSession";
import { ALL_SPACES_STORAGE_KEY } from "../../../shared/state/spaceScope";
import { jsonResponse, spaces, spaceListResponse, userProfile } from "../../../test/testData";
import { SpacesPage } from "../pages/SpacesPage";

function renderSpacesPage() {
  window.localStorage.setItem(AUTH_ACCESS_TOKEN_STORAGE_KEY, "token");

  render(
    <MemoryRouter>
      <AppProviders>
        <SpacesPage />
      </AppProviders>
    </MemoryRouter>
  );
}

function stubSpacesApi(initialSpaces: SpaceResponse[]) {
  let currentSpaces = [...initialSpaces];
  const requests: Array<{ body: unknown; method: string; url: string }> = [];

  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? "GET";
      const body = init?.body ? JSON.parse(String(init.body)) : null;
      requests.push({ body, method, url });

      if (url.includes("/api/v1/auth/me")) {
        return jsonResponse(userProfile);
      }

      if (url.includes("/api/v1/spaces") && method === "GET") {
        return jsonResponse({ items: currentSpaces });
      }

      if (url.endsWith("/api/v1/spaces") && method === "POST") {
        const created = {
          ...spaceListResponse.items[0],
          description: null,
          document_count: 0,
          id: "77777777-7777-7777-7777-777777777777",
          is_default: false,
          name: String((body as { name: string }).name),
          tracked_field_count: 0
        };
        currentSpaces = [...currentSpaces, created];
        return jsonResponse(created, { status: 201 });
      }

      if (url.includes("/api/v1/spaces/") && method === "PATCH") {
        const spaceId = url.split("/api/v1/spaces/")[1];
        const payload = body as Partial<SpaceResponse> & { is_default?: boolean };
        currentSpaces = currentSpaces.map((space) => {
          if (payload.is_default && space.id !== spaceId) {
            return { ...space, is_default: false };
          }
          if (space.id !== spaceId) {
            return space;
          }
          return {
            ...space,
            description: payload.description ?? space.description,
            is_default: payload.is_default ?? space.is_default,
            name: payload.name ?? space.name
          };
        });
        return jsonResponse(currentSpaces.find((space) => space.id === spaceId));
      }

      if (url.includes("/api/v1/spaces/") && method === "DELETE") {
        const spaceId = url.split("/api/v1/spaces/")[1];
        currentSpaces = currentSpaces.map((space) =>
          space.id === spaceId ? { ...space, archived_at: "2026-06-24T17:00:00Z" } : space
        );
        return jsonResponse(currentSpaces.find((space) => space.id === spaceId));
      }

      return jsonResponse({}, { status: 404 });
    })
  );

  return { requests };
}

describe("SpacesPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("creates a Space from the inline name-only form and renders active Spaces as a table", async () => {
    window.localStorage.setItem(ALL_SPACES_STORAGE_KEY, "true");
    const { requests } = stubSpacesApi(spaces);

    renderSpacesPage();

    const user = userEvent.setup();
    await waitFor(() => expect(screen.getByText("All-spaces mode is on")).toBeInTheDocument());
    await waitFor(() => expect(screen.getByText("Core Space")).toBeInTheDocument());
    expect(screen.getByRole("columnheader", { name: "Documents" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Pins" })).toBeInTheDocument();
    expect(screen.queryByLabelText("Description")).not.toBeInTheDocument();
    const coreSpaceRow = screen.getByRole("row", { name: /Core Space/ });
    expect(within(coreSpaceRow).getByRole("cell", { name: "1" })).toBeInTheDocument();
    expect(within(coreSpaceRow).getByRole("cell", { name: "2" })).toBeInTheDocument();

    await user.type(screen.getByLabelText("Name"), "New Space");
    await user.click(screen.getByRole("button", { name: "Create Space" }));

    await waitFor(() => expect(screen.getByText("New Space")).toBeInTheDocument());
    expect(requests.find((request) => request.method === "POST")?.body).toEqual({
      name: "New Space"
    });
  });

  it("edits Space details and marks a non-default Space as default from the popover", async () => {
    const { requests } = stubSpacesApi(spaces);

    renderSpacesPage();

    const user = userEvent.setup();
    await waitFor(() => expect(screen.getByText("Archive Prep")).toBeInTheDocument());

    const archivePrepRow = screen.getByRole("row", { name: /Archive Prep/ });
    await user.click(within(archivePrepRow).getByRole("button", { name: "Edit" }));

    const editForm = screen.getByText("Edit Space").closest("form");
    expect(editForm).not.toBeNull();
    const nameField = within(editForm as HTMLFormElement).getByLabelText("Name");
    await user.clear(nameField);
    await user.type(nameField, "Updated Space");
    await user.type(within(editForm as HTMLFormElement).getByLabelText("Description"), " with notes");
    await user.click(within(editForm as HTMLFormElement).getByRole("button", { name: "Default" }));
    await user.click(within(editForm as HTMLFormElement).getByRole("button", { name: "Save" }));

    await waitFor(() => expect(screen.getByText("Updated Space")).toBeInTheDocument());
    expect(requests.find((request) => request.method === "PATCH")?.body).toEqual({
      description: "Secondary workspace with notes",
      is_default: true,
      name: "Updated Space"
    });
  });

  it("archives non-default Spaces and leaves the current default archive action disabled", async () => {
    stubSpacesApi(spaces);

    renderSpacesPage();

    const user = userEvent.setup();
    await waitFor(() => expect(screen.getByText("Core Space")).toBeInTheDocument());

    const coreSpaceRow = screen.getByRole("row", { name: /Core Space/ });
    expect(within(coreSpaceRow).getByRole("button", { name: "Archive" })).toBeDisabled();

    const archivePrepRow = screen.getByRole("row", { name: /Archive Prep/ });
    await user.click(within(archivePrepRow).getByRole("button", { name: "Archive" }));

    await waitFor(() => expect(screen.queryByRole("row", { name: /Archive Prep/ })).not.toBeInTheDocument());
    expect(screen.getByText("1 archived")).toBeInTheDocument();
  });
});
