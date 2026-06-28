import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppProviders } from "../../../app/providers";
import { AUTH_ACCESS_TOKEN_STORAGE_KEY } from "../../../shared/state/authSession";
import { adminProfile, jsonResponse, spaceListResponse } from "../../../test/testData";
import { AdminHomePage } from "../pages/AdminHomePage";

describe("AdminHomePage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("loads runtime status, limits, and updates a selected user", async () => {
    window.localStorage.setItem(AUTH_ACCESS_TOKEN_STORAGE_KEY, "admin-token");

    let selectedUser = {
      created_at: "2026-06-22T17:00:00Z",
      email: "member@example.com",
      full_name: "Member User",
      id: "99999999-9999-9999-9999-999999999999",
      is_active: true,
      is_admin: false,
      last_login: "2026-06-22T17:10:00Z",
      must_change_password: false,
      updated_at: "2026-06-22T17:11:00Z",
    };

    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.includes("/api/v1/auth/me")) {
          return jsonResponse(adminProfile);
        }
        if (url.includes("/api/v1/spaces")) {
          return jsonResponse(spaceListResponse);
        }
        if (url.includes("/api/v1/admin/users/") && init?.method === "PATCH") {
          selectedUser = { ...selectedUser, is_admin: true };
          return jsonResponse(selectedUser);
        }
        if (url.includes("/api/v1/admin/users/")) {
          return jsonResponse(selectedUser);
        }
        if (url.includes("/api/v1/admin/users")) {
          return jsonResponse({
            items: [selectedUser],
            page: 1,
            page_size: 25,
            total: 1,
          });
        }
        if (url.includes("/api/v1/admin/effective-limits")) {
          return jsonResponse({
            documents: null,
            max_file_size_bytes: 104857600,
            chunks: null,
            storage_bytes: null,
            tokens_5h: null,
            tokens_week: null,
            retrieval_chunks: 20,
            output_tokens: 2400,
            per_document_chunks: 2000,
            upload_rate_limit: {
              enabled: true,
              requests: 10,
              window_seconds: 60,
            },
          });
        }
        if (url.includes("/status?type=json")) {
          return jsonResponse({
            application: {
              environment: "development",
              generated_at: "2026-06-22T17:00:00Z",
              name: "Ragdoll API",
              version: "0.1.0",
            },
            ollama: {
              catalog_reachable: true,
              configured_base_url: true,
              configured_models: [],
              detail: "ok",
              status: "healthy",
            },
            services: {
              database: { detail: "ok", status: "healthy" },
              graph: { detail: "ok", status: "healthy" },
              llm: { detail: "ok", status: "healthy" },
              queue: { detail: "ok", status: "healthy" },
              storage: { detail: "ok", status: "healthy" },
              vector: { detail: "ok", status: "healthy" },
            },
            status: "ok",
            supabase: {
              backend: "supabase",
              detail: "ok",
              services: {},
              status: "healthy",
            },
          });
        }
        return jsonResponse({}, { status: 404 });
      })
    );

    render(
      <MemoryRouter>
        <AppProviders>
          <AdminHomePage />
        </AppProviders>
      </MemoryRouter>
    );

    const user = userEvent.setup();
    await waitFor(() => expect(screen.getByText("Operator admin")).toBeInTheDocument());
    await waitFor(() => expect(screen.getByText("member@example.com")).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: "Inspect" }));
    await waitFor(() => expect(screen.getByLabelText("Admin access")).toBeInTheDocument());
    await user.click(screen.getByLabelText("Admin access"));

    await waitFor(() => expect(screen.getByText("User settings updated.")).toBeInTheDocument());
  });
});
