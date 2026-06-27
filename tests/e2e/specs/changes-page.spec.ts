import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

const API_BASE_URL = process.env.E2E_API_BASE_URL ?? "http://backend:8000";

function uniqueEmail(label: string) {
  return `${label}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`;
}

function uniqueDocumentName() {
  return `changes-accordion-${Date.now()}.txt`;
}

function uniqueCorrectionValue() {
  return `Correction value ${Date.now()} ${Math.random().toString(36).slice(2, 8)}`;
}

function buildChunkHeavyUpload() {
  return Array.from(
    { length: 4500 },
    (_, index) => `Acme Operations ${index} coordinates with Redwood Systems on document workflows.`
  ).join(" ");
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
  await expect(page).toHaveURL(/\/dashboard$/);
}

async function readAccessToken(page: Page) {
  const token = await page.evaluate(() =>
    window.localStorage.getItem("ragdoll.auth.accessToken")
  );
  expect(token).toBeTruthy();
  return token as string;
}

async function createCorrection(
  request: APIRequestContext,
  token: string,
  proposedValue: string,
  rationale: string
) {
  const response = await request.post(`${API_BASE_URL}/api/v1/corrections`, {
    data: {
      proposed_value: proposedValue,
      rationale
    },
    headers: {
      Authorization: `Bearer ${token}`
    }
  });

  expect(response.ok()).toBeTruthy();
  return response.json();
}

test.describe("changes page accordions", () => {
  test("activity accordion fetches detail once and reuses it after collapse", async ({
    page
  }) => {
    const email = uniqueEmail("changes-activity");
    const password = "testpass123";
    const uploadName = uniqueDocumentName();

    await register(page, email, password);
    await login(page, email, password);

    await page.goto("/documents");
    await expect(page.getByRole("heading", { name: "Documents", exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Upload" }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await page.getByRole("dialog").locator("input[type='file']").setInputFiles({
      buffer: Buffer.from(buildChunkHeavyUpload()),
      mimeType: "text/plain",
      name: uploadName
    });
    await page.getByRole("button", { name: "Close" }).click();

    const documentRow = page.locator("tbody tr", { hasText: uploadName }).first();
    await expect(documentRow).toContainText(uploadName);
    await expect.poll(async () => (await documentRow.textContent()) ?? "", {
      message: "document processing should complete before the change event is reviewed",
      timeout: 30000
    }).toContain("Completed");

    let changeDetailRequests = 0;
    await page.route("**/api/v1/changes/*", async (route) => {
      const pathname = new URL(route.request().url()).pathname;
      if (/\/api\/v1\/changes\/[^/]+$/.test(pathname)) {
        changeDetailRequests += 1;
      }
      await route.continue();
    });

    await page.goto("/changes");

    const activityAccordion = page.getByTestId("changes-activity-accordion");
    const trigger = activityAccordion
      .getByRole("button", { name: new RegExp(uploadName.replace(".", "\\."), "i") })
      .first();

    await expect(trigger).toBeVisible();
    await trigger.click();
    await expect(activityAccordion.getByRole("button", { name: "Mark read" })).toBeVisible();
    await expect.poll(() => changeDetailRequests).toBe(1);

    await trigger.click();
    await trigger.click();
    await expect(activityAccordion.getByRole("button", { name: "Mark read" })).toBeVisible();
    await expect.poll(() => changeDetailRequests).toBe(1);
  });

  test("corrections accordion deep link fetches detail once and keeps inline review working", async ({
    page,
    request
  }) => {
    const email = uniqueEmail("changes-corrections");
    const password = "testpass123";
    const proposedValue = uniqueCorrectionValue();

    await register(page, email, password);
    await login(page, email, password);

    const token = await readAccessToken(page);
    const correction = await createCorrection(
      request,
      token,
      proposedValue,
      "The answer should use the more precise value."
    );

    let correctionDetailRequests = 0;
    await page.route("**/api/v1/corrections/*", async (route) => {
      const pathname = new URL(route.request().url()).pathname;
      if (/\/api\/v1\/corrections\/[^/]+$/.test(pathname)) {
        correctionDetailRequests += 1;
      }
      await route.continue();
    });

    await page.goto(`/changes?tab=corrections&correction_id=${correction.id}&status=pending`);

    const correctionsAccordion = page.getByTestId("changes-corrections-accordion");
    const trigger = correctionsAccordion
      .getByRole("button", { name: new RegExp(proposedValue, "i") })
      .first();

    await expect(trigger).toBeVisible();
    await expect(correctionsAccordion.getByLabel("Review notes")).toBeVisible();
    await expect.poll(() => correctionDetailRequests).toBe(1);

    await trigger.click();
    await trigger.click();
    await expect(correctionsAccordion.getByLabel("Review notes")).toBeVisible();
    await expect.poll(() => correctionDetailRequests).toBe(1);

    await correctionsAccordion.getByLabel("Review notes").fill("Confirmed from review.");
    await correctionsAccordion.getByRole("button", { name: "Verify" }).click();

    await expect(page.getByText("Correction verified.")).toBeVisible();
    await expect(correctionsAccordion.getByText("verified").first()).toBeVisible();
    await expect.poll(() => correctionDetailRequests).toBe(1);
  });
});
