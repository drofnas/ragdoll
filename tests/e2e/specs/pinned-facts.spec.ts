import { expect, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

import { authenticatedTest as test } from "../helpers/shared-user";

const API_BASE_URL = process.env.E2E_API_BASE_URL ?? "http://backend:8000";
const FRONTEND_STACK_QUERY =
  "What is the technology stack used for the Frontend Web UI? Return a bulleted list with just the tech stack for it.";
const FRONTEND_STACK_FIXTURE_PATH = path.resolve(process.cwd(), "fixtures/frontend-web-ui-stack.md");
const ARCHITECTURE_DOC_UPLOAD_PATHS = [
  path.resolve(process.cwd(), "../../docs/api-v1-module-inventory.md"),
  path.resolve(process.cwd(), "../../docs/architecture/README.md"),
  path.resolve(process.cwd(), "../../docs/architecture/backend-architecture.md"),
  path.resolve(process.cwd(), "../../docs/architecture/capability-map.md"),
  path.resolve(process.cwd(), "../../docs/architecture/cross-cutting-concerns.md"),
  path.resolve(process.cwd(), "../../docs/architecture/data-and-storage.md"),
  path.resolve(process.cwd(), "../../docs/architecture/frontend-architecture.md"),
  path.resolve(process.cwd(), "../../docs/architecture/ingestion-and-processing.md"),
  path.resolve(process.cwd(), "../../docs/architecture/retrieval-chat-and-discovery.md"),
  path.resolve(process.cwd(), "../../docs/architecture/system-overview.md")
];

function uniqueFactName() {
  return `Pinned fact ${Date.now()}`;
}

function uniqueFactKey() {
  return `pinned_fact_${Date.now()}`;
}

function uniqueDocumentName() {
  return `pinned-facts-${Date.now()}.txt`;
}

function uniqueMarkdownDocumentName() {
  return `frontend-stack-${Date.now()}.md`;
}

async function waitForDocumentProcessing(page: Page, uploadName: string, message: string) {
  const documentRow = page.locator("tbody tr", { hasText: uploadName }).first();
  await expect(documentRow).toContainText(uploadName);
  await expect.poll(async () => (await documentRow.textContent()) ?? "", {
    message,
    timeout: 30000
  }).toContain("Completed");
}

test.describe("pinned facts", () => {
  test("creates a pinned fact from document evidence and records manual edits in history", async ({
    page,
    request,
    sharedUser
  }) => {
    const uploadName = uniqueDocumentName();
    const factName = uniqueFactName();
    const factKey = uniqueFactKey();

    await page.goto("/documents");
    await expect(page.getByRole("heading", { name: "Documents", exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Upload" }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await page.getByRole("dialog").locator("input[type='file']").setInputFiles({
      buffer: Buffer.from("FastAPI powers the API service and remains the current backend framework."),
      mimeType: "text/plain",
      name: uploadName
    });
    await page.getByRole("button", { name: "Close" }).click();

    await waitForDocumentProcessing(page, uploadName, "document processing should complete before creating a pinned fact");

    await page.goto("/pinned-facts/create");
    await page.getByLabel("Name").fill(factName);
    await page.getByLabel("Key").fill(factKey);
    await page.getByLabel("Detection query").fill("FastAPI powers the API service");
    await page.getByLabel("Stored value").fill("FastAPI");
    await page.getByRole("button", { name: "Test Query" }).click();

    await expect(page.getByText("Assistant preview")).toBeVisible();
    await expect(page.getByText("Used for synthesis").first()).toBeVisible();
    await expect(page.getByRole("button", { name: "Create" })).toBeEnabled();
    await page.getByRole("button", { name: "Create" }).click();

    await expect(page).toHaveURL(/\/pinned-facts$/, { timeout: 30000 });
    const listResponse = await request.get(`${API_BASE_URL}/api/v1/pinned-facts`, {
      headers: {
        Authorization: `Bearer ${sharedUser.accessToken}`
      }
    });
    expect(listResponse.ok(), await listResponse.text()).toBeTruthy();
    const listPayload = (await listResponse.json()) as { items: Array<{ id: string; key: string }> };
    const createdFact = listPayload.items.find((item) => item.key === factKey);
    expect(createdFact).toBeTruthy();

    await page.goto(`/pinned-facts/${createdFact?.id}`);

    await expect(page.getByText("Current value")).toBeVisible();
    await page.getByRole("button", { name: "Edit stored value" }).click();
    await page.getByLabel("Stored value").fill("Starlette");
    await page.getByLabel("Update note").fill("Manual verification note");
    await page.getByRole("button", { name: "Save edit" }).click();

    await expect(page.getByText("Stored value updated.")).toBeVisible();
    await expect(page.getByText("Manual verification note")).toBeVisible();
  });

  test("pins a fact from a chat answer", async ({ page, request, sharedUser }) => {
    const uploadName = uniqueDocumentName();
    const factName = uniqueFactName();
    const factKey = uniqueFactKey();

    await page.goto("/documents");
    await expect(page.getByRole("heading", { name: "Documents", exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Upload" }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await page.getByRole("dialog").locator("input[type='file']").setInputFiles({
      buffer: Buffer.from("Atlas is the current project codename for the workspace."),
      mimeType: "text/plain",
      name: uploadName
    });
    await page.getByRole("button", { name: "Close" }).click();

    await waitForDocumentProcessing(page, uploadName, "document processing should complete before pinning from chat");

    await page.goto("/chat");
    await page.getByRole("button", { name: "New session" }).click();
    await expect(page).toHaveURL(/\/chat\/.+$/, { timeout: 30000 });

    await page.getByRole("textbox", { name: "Message" }).fill("What is the current project codename?");
    await page.getByRole("button", { name: "Send message" }).click();

    await expect(page.getByRole("link", { name: "Pin as fact" })).toBeVisible({ timeout: 30000 });
    await page.getByRole("link", { name: "Pin as fact" }).click();

    await expect(page).toHaveURL(/\/pinned-facts\/create$/, { timeout: 30000 });
    await expect(page.getByText("Seeded from chat")).toBeVisible();
    await expect(page.getByLabel("Detection query")).toHaveValue("What is the current project codename?");

    await page.getByLabel("Name").fill(factName);
    await page.getByLabel("Key").fill(factKey);
    await expect(page.getByLabel("Stored value")).toHaveValue(/atlas/i);
    await page.getByRole("button", { name: "Create" }).click();

    await expect(page).toHaveURL(/\/pinned-facts$/, { timeout: 30000 });
    const listResponse = await request.get(`${API_BASE_URL}/api/v1/pinned-facts`, {
      headers: {
        Authorization: `Bearer ${sharedUser.accessToken}`
      }
    });
    expect(listResponse.ok(), await listResponse.text()).toBeTruthy();
    const listPayload = (await listResponse.json()) as { items: Array<{ key: string; title: string }> };
    expect(listPayload.items.some((item) => item.key === factKey && item.title === factName)).toBeTruthy();
  });

  test("uses the same markdown evidence successfully in chat and pinned fact detection", async ({
    page,
    sharedUser
  }) => {
    void sharedUser;
    const uploadName = uniqueMarkdownDocumentName();
    const factName = uniqueFactName();
    const factKey = uniqueFactKey();

    await page.goto("/documents");
    await expect(page.getByRole("heading", { name: "Documents", exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Upload" }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await page.getByRole("dialog").locator("input[type='file']").setInputFiles({
      name: uploadName,
      mimeType: "text/markdown",
      buffer: fs.readFileSync(FRONTEND_STACK_FIXTURE_PATH)
    });
    await page.getByRole("button", { name: "Close" }).click();

    await waitForDocumentProcessing(page, uploadName, "markdown processing should complete before cross-flow verification");

    await page.goto("/chat");
    await page.getByRole("button", { name: "New session" }).click();
    await expect(page).toHaveURL(/\/chat\/.+$/, { timeout: 30000 });
    await page.getByRole("textbox", { name: "Message" }).fill(FRONTEND_STACK_QUERY);
    await page.getByRole("button", { name: "Send message" }).click();

    await expect(page.getByText(/react/i).first()).toBeVisible({ timeout: 30000 });
    await expect(page.getByText(/tailwind/i).first()).toBeVisible();
    await expect(page.getByText(/vite/i).first()).toBeVisible();

    await page.goto("/pinned-facts/create");
    await page.getByLabel("Name").fill(factName);
    await page.getByLabel("Key").fill(factKey);
    await page.getByLabel("Detection query").fill(FRONTEND_STACK_QUERY);
    await page.getByRole("button", { name: "Test Query" }).click();

    await expect(page.getByText("Assistant preview")).toBeVisible({ timeout: 30000 });
    await expect(page.getByText("Pinned-fact action failed")).toHaveCount(0);
    await expect(page.getByText("Used for synthesis").first()).toBeVisible();
    await page.getByRole("button", { name: "Use as Stored Value" }).first().click();
    await expect(page.getByLabel("Stored value")).toHaveValue(/react|tailwind|vite/i);
    await expect(page.getByRole("button", { name: "Create" })).toBeEnabled();
  });

  test("uploads the real architecture docs set and shows a chat-style pinned-fact preview for the frontend stack query", async ({
    page,
    sharedUser
  }) => {
    void sharedUser;
    const factName = uniqueFactName();
    const factKey = uniqueFactKey();

    for (const docPath of ARCHITECTURE_DOC_UPLOAD_PATHS) {
      expect(fs.existsSync(docPath), `missing upload fixture: ${docPath}`).toBeTruthy();
    }

    await page.goto("/documents");
    await expect(page.getByRole("heading", { name: "Documents", exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Upload" }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await page.getByRole("dialog").locator("input[type='file']").setInputFiles(ARCHITECTURE_DOC_UPLOAD_PATHS);
    await page.getByRole("button", { name: "Close" }).click();

    for (const docPath of ARCHITECTURE_DOC_UPLOAD_PATHS) {
      await waitForDocumentProcessing(
        page,
        path.basename(docPath),
        `document processing should complete for ${path.basename(docPath)}`
      );
    }

    await page.goto("/chat");
    await page.getByRole("button", { name: "New session" }).click();
    await expect(page).toHaveURL(/\/chat\/.+$/, { timeout: 30000 });
    await page.getByRole("textbox", { name: "Message" }).fill(FRONTEND_STACK_QUERY);
    await page.getByRole("button", { name: "Send message" }).click();

    await expect(page.getByText(/tailwind css v4/i).first()).toBeVisible({ timeout: 30000 });
    await expect(page.getByText(/vite plugin|vite/i).first()).toBeVisible();

    await page.goto("/pinned-facts/create");
    await page.getByLabel("Name").fill(factName);
    await page.getByLabel("Key").fill(factKey);
    await page.getByLabel("Detection query").fill(FRONTEND_STACK_QUERY);
    await page.getByRole("button", { name: "Test Query" }).click();

    await expect(page.getByText("Assistant preview")).toBeVisible({ timeout: 30000 });
    await expect(page.getByText("Pinned-fact action failed")).toHaveCount(0);
    await expect(page.getByText("Used for synthesis").first()).toBeVisible();
    await page.getByRole("button", { name: "Use as Stored Value" }).first().click();
    await expect(page.getByLabel("Stored value")).toHaveValue(/tailwind|vite/i);
    await expect(page.getByRole("button", { name: "Create" })).toBeEnabled();
  });
});
