import { expect, test } from "@playwright/test";

test.describe("shell smoke", () => {
  test("public home renders the workspace title", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Ragdoll Workspace" })).toBeVisible();
  });

  test("anonymous dashboard navigation redirects to login", async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.clear();
    });
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  });
});
