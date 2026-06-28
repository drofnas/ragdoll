import { expect, test as base, type APIRequestContext, type Page } from "@playwright/test";

const API_BASE_URL = process.env.E2E_API_BASE_URL ?? "http://backend:8000";
const TEST_USER_EMAIL = process.env.E2E_TEST_USER_EMAIL ?? "tests@ragdoll.local";
const TEST_USER_PASSWORD = process.env.E2E_TEST_USER_PASSWORD ?? "testpass123";
const TEST_USER_FULL_NAME = process.env.E2E_TEST_USER_FULL_NAME ?? "Ragdoll E2E Test User";
const AUTH_ACCESS_TOKEN_STORAGE_KEY = "ragdoll.auth.accessToken";

export interface SharedUserSession {
  accessToken: string;
  email: string;
  password: string;
  provisionedThisRun: boolean;
}

async function clearBrowserSession(page: Page) {
  await page.context().clearCookies();
  await page.goto("/login");
  await page.evaluate(() => {
    window.localStorage.clear();
  });
}

async function waitForAuthOutcome(
  page: Page,
  {
    successPath,
    failureTitle,
    timeoutMs = 10_000
  }: {
    successPath: string;
    failureTitle: string;
    timeoutMs?: number;
  }
): Promise<{ success: boolean; errorMessage?: string }> {
  const deadline = Date.now() + timeoutMs;
  const failureAlert = page.locator("[role='alert']");

  while (Date.now() < deadline) {
    const pathname = new URL(page.url()).pathname;
    if (pathname === successPath) {
      return { success: true };
    }

    if (await page.getByText(failureTitle, { exact: true }).isVisible()) {
      return {
        success: false,
        errorMessage: ((await failureAlert.textContent()) ?? failureTitle).trim()
      };
    }

    await page.waitForTimeout(100);
  }

  throw new Error(`Timed out waiting for ${successPath} or "${failureTitle}".`);
}

async function attemptLogin(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(TEST_USER_EMAIL);
  await page.getByLabel("Password").fill(TEST_USER_PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  return waitForAuthOutcome(page, {
    successPath: "/dashboard",
    failureTitle: "Sign-in failed"
  });
}

async function attemptRegistration(page: Page) {
  await page.goto("/register");
  await page.getByLabel("Full name").fill(TEST_USER_FULL_NAME);
  await page.getByLabel("Email").fill(TEST_USER_EMAIL);
  await page.getByLabel("Password").fill(TEST_USER_PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
  return waitForAuthOutcome(page, {
    successPath: "/login",
    failureTitle: "Registration failed"
  });
}

async function readAccessToken(page: Page) {
  const token = await page.evaluate((storageKey) => window.localStorage.getItem(storageKey), AUTH_ACCESS_TOKEN_STORAGE_KEY);
  expect(token).toBeTruthy();
  return token as string;
}

async function resetWorkspace(request: APIRequestContext, accessToken: string) {
  const response = await request.post(`${API_BASE_URL}/api/v1/auth/e2e/reset-workspace`, {
    headers: {
      Authorization: `Bearer ${accessToken}`
    }
  });

  expect(response.ok(), await response.text()).toBeTruthy();
}

async function ensureSharedUserSession(page: Page, request: APIRequestContext): Promise<SharedUserSession> {
  await clearBrowserSession(page);

  let provisionedThisRun = false;
  let loginAttempt = await attemptLogin(page);
  if (!loginAttempt.success) {
    if (!loginAttempt.errorMessage?.includes("Incorrect username or password.")) {
      throw new Error(`Shared E2E user login failed unexpectedly: ${loginAttempt.errorMessage}`);
    }

    const registrationAttempt = await attemptRegistration(page);
    if (!registrationAttempt.success && !registrationAttempt.errorMessage?.includes("Email already registered.")) {
      throw new Error(`Shared E2E user registration failed unexpectedly: ${registrationAttempt.errorMessage}`);
    }

    provisionedThisRun = registrationAttempt.success;
    loginAttempt = await attemptLogin(page);
    if (!loginAttempt.success) {
      throw new Error(
        `Shared E2E user could not sign in after registration flow: ${loginAttempt.errorMessage}`
      );
    }
  }

  const accessToken = await readAccessToken(page);
  await resetWorkspace(request, accessToken);
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/dashboard$/);

  return {
    accessToken,
    email: TEST_USER_EMAIL,
    password: TEST_USER_PASSWORD,
    provisionedThisRun
  };
}

export const authenticatedTest = base.extend<{ sharedUser: SharedUserSession }>({
  sharedUser: async ({ page, request }, use) => {
    const session = await ensureSharedUserSession(page, request);

    try {
      await use(session);
    } finally {
      await resetWorkspace(request, session.accessToken);
      await clearBrowserSession(page);
    }
  }
});
