import { expect, test, type Page } from "@playwright/test";

function uniqueEmail(label: string) {
  return `${label}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`;
}

async function register(page: Page, email: string, password: string) {
  await page.goto("/register");
  await page.getByLabel("Full name").fill("E2E User");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/login$/);
}

async function login(page: Page, email: string, password: string) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
}

test.describe("self-hosted public and auth flows", () => {
  test("registration returns to login with a success message", async ({ page }) => {
    const email = uniqueEmail("register");
    const password = "testpass123";

    await register(page, email, password);

    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByText("Account ready")).toBeVisible();
    await expect(page.getByLabel("Email")).toHaveValue(email);
  });

  test("public status link opens the web status page", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "Status" }).click();
    await expect(page).toHaveURL(/\/status$/);
    await expect(page.getByRole("heading", { name: "Workspace status" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Service overview" })).toBeVisible();
  });

  test("registered users can sign in and upload a document", async ({ page }) => {
    const email = uniqueEmail("workspace");
    const password = "testpass123";

    await register(page, email, password);
    await login(page, email, password);

    await expect(page).toHaveURL(/\/dashboard$/);
    await expect(page.getByText("Workspace dashboard")).toBeVisible();

    await page.goto("/documents");
    await expect(page.getByRole("heading", { name: "Documents" })).toBeVisible();

    await page.locator("input[type='file']").setInputFiles({
      buffer: Buffer.from("hello from playwright"),
      mimeType: "text/plain",
      name: "e2e-upload.txt"
    });
    await page.getByRole("button", { name: "Upload" }).click();

    await expect(page).toHaveURL(/\/documents\/.+/);
    await expect(page.getByRole("heading", { name: "e2e-upload.txt" })).toBeVisible();
    await expect.poll(async () => (await page.locator("body").textContent()) ?? "", {
      message: "document processing should complete in the dedicated worker"
    }).toContain("Overall: completed");
    await expect(page.locator("body")).toContainText("hello from playwright");
  });
});
