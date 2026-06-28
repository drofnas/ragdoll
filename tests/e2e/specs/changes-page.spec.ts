import { expect, type APIRequestContext } from "@playwright/test";

import { authenticatedTest as test } from "../helpers/shared-user";

const API_BASE_URL = process.env.E2E_API_BASE_URL ?? "http://backend:8000";

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
    page,
    sharedUser
  }) => {
    void sharedUser;
    const uploadName = uniqueDocumentName();

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
    request,
    sharedUser
  }) => {
    const proposedValue = uniqueCorrectionValue();
    const correction = await createCorrection(
      request,
      sharedUser.accessToken,
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
