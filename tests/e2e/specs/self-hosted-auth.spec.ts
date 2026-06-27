import { expect, test } from "@playwright/test";

import { authenticatedTest } from "../helpers/shared-user";

function buildChunkHeavyUpload() {
  return Array.from(
    { length: 4500 },
    (_, index) => `Acme Operations ${index} coordinates with Redwood Systems on document workflows.`
  ).join(" ");
}

test("public status link opens the web status page", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Status" }).click();
  await expect(page).toHaveURL(/\/status$/);
  await expect(page.getByRole("heading", { name: "Workspace status" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Service overview" })).toBeVisible();
});

authenticatedTest("shared test user can sign in and reach the account workspace", async ({
  page,
  sharedUser
}) => {
  await expect(page.getByText("Workspace dashboard")).toBeVisible();

  await page.goto("/account");
  await expect(page.getByLabel("Email")).toHaveValue(sharedUser.email);
});

authenticatedTest("shared test user can upload a document", async ({ page, sharedUser }) => {
  void sharedUser;
  await page.goto("/documents");
  await expect(page.getByRole("heading", { name: "Documents", exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Upload" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();

  await page.getByRole("dialog").locator("input[type='file']").setInputFiles({
    buffer: Buffer.from(buildChunkHeavyUpload()),
    mimeType: "text/plain",
    name: "e2e-upload.txt"
  });
  await page.getByRole("button", { name: "Close" }).click();

  await expect(page).toHaveURL(/\/documents$/);
  const documentRow = page.locator("tbody tr", { hasText: "e2e-upload.txt" }).first();
  await expect(documentRow).toContainText("e2e-upload.txt");
  await expect(page.getByRole("columnheader", { name: "Chunk Status" })).toBeVisible();
  await expect.poll(
    async () => {
      const text = (await documentRow.textContent()) ?? "";
      const visibleStatus = ["Queued", "Parsing", "Vectorizing", "Extracting", "Graphing"].find(
        (label) => text.includes(label)
      );
      return visibleStatus ?? "";
    },
    {
      message: "Documents page should show a live queue-backed chunk status before completion",
      timeout: 20000
    }
  ).not.toBe("");
  await expect.poll(async () => (await page.locator("table").textContent()) ?? "", {
    message: "document processing should complete in the document-vector worker",
    timeout: 30000
  }).toContain("Completed");
  await expect(page.getByRole("link", { name: "View" }).first()).toBeVisible();
});
