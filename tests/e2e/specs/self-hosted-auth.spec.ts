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

  test("public status link resolves to the backend status page", async ({ page, request }) => {
    await page.goto("/");

    const statusHref = await page.getByRole("link", { name: "Status" }).getAttribute("href");
    expect(statusHref).toBeTruthy();

    const response = await request.get(statusHref!);
    expect(response.ok()).toBeTruthy();
    expect(response.status()).toBe(200);
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
  });
});
