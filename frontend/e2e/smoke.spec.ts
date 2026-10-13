import { expect, test } from "@playwright/test";

const API =
  process.env.NEXT_PUBLIC_API_URL || "https://sospana-sonke-api-fra.onrender.com/api/v1";

test("search submits a keyword and shows the stored-role result", async ({ page }) => {
  await page.goto("/jobs");
  await expect(page.getByRole("heading", { name: "Open roles the scanner has stored" })).toBeVisible();
  await page.getByLabel("Keyword").fill("nurse");
  await page.getByRole("button", { name: "Search stored roles" }).click();
  await expect(page).toHaveURL(/\/jobs\?.*q=nurse/);
  await expect(
    page.getByText(/open roles that match|No stored roles match|The role index could not be reached/),
  ).toBeVisible();
});

test("opportunities search keeps the programme heading", async ({ page }) => {
  await page.goto("/opportunities");
  await expect(
    page.getByRole("heading", { name: "Internships, learnerships, bursaries and graduate programmes" }),
  ).toBeVisible();
  await page.getByLabel("Keyword").fill("engineering");
  await page.getByRole("button", { name: "Show stored programmes" }).click();
  await expect(page).toHaveURL(/\/opportunities\?.*q=engineering/);
  await expect(
    page.getByText(/Closing dates that were not stated|Not enough data|The list could not be reached/),
  ).toBeVisible();
});

test("an employer page shows the stored careers link", async ({ page }) => {
  const response = await fetch(`${API}/jobs?limit=1`);
  expect(response.ok).toBeTruthy();
  const data = (await response.json()) as { jobs?: { company_id?: string; company_name?: string }[] };
  const job = data.jobs?.[0];
  expect(job?.company_id).toBeTruthy();
  await page.goto(`/employers/${job!.company_id}`);
  await expect(page.getByRole("heading", { level: 1, name: job!.company_name! })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Careers link" })).toBeVisible();
});

test("sign-up stays on the form until consent, and is not submitted", async ({ page }) => {
  await page.goto("/register");
  await expect(page.getByRole("heading", { name: "Create your account" })).toBeVisible();
  const submit = page.getByRole("button", { name: "Create account" });
  await expect(submit).toBeDisabled();
  await page.getByRole("checkbox").check();
  await expect(submit).toBeEnabled();
  const alerts = page.getByRole("radiogroup", { name: /email me about a post/ });
  await alerts.getByRole("radio", { name: "No" }).check();
  await expect(page).toHaveURL(/\/register$/);
  await expect(submit).toBeEnabled();
});

test("alerts preferences send a signed-out visitor to sign-in", async ({ page }) => {
  await page.goto("/preferences");
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("heading", { name: "Sospana Sonke" })).toBeVisible();
});
