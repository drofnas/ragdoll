import { expect, test } from "@playwright/test";

test.describe("shell smoke", () => {
  test("public home renders the Phase 1 scaffold title", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Ragdoll Clean-Room Rebuild" })).toBeVisible();
  });

  test("anonymous dashboard navigation redirects to login", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByRole("heading", { name: "Login Placeholder" })).toBeVisible();
  });
});
