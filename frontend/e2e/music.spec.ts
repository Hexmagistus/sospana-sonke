import { expect, test } from "@playwright/test";

// Ids from each release page's bc-page-properties, checked in the EmbeddedPlayer HTML.
const EMBEDS: [string, string][] = [
  ["COLONIZERS ARE COMING BACK", "track=3499065470"],
  ["MAN AND MEMORY", "album=3713535762"],
  ["ELI DNA 2", "album=3347381230"],
  ["LODEWYKXS", "album=594928023"],
  ["SANCTUM SANCTORUM", "album=3481409865"],
  ["uCansi", "album=1529620876"],
  ["N.E.O", "album=686813694"],
  ["ELI DNA", "album=942910523"],
  ["INITIATES OF THE FLAME", "album=744084806"],
];

test("music page embeds every GASTRIC release, newest first", async ({ page }) => {
  await page.goto("/music");
  await expect(page.getByRole("heading", { level: 1, name: "Music" })).toBeVisible();
  const frames = page.locator("main iframe[src*='bandcamp.com/EmbeddedPlayer']");
  await expect(frames).toHaveCount(EMBEDS.length);
  for (let i = 0; i < EMBEDS.length; i += 1) {
    const [title, id] = EMBEDS[i];
    const frame = frames.nth(i);
    await expect(frame).toHaveAttribute("title", `${title} by GASTRIC on Bandcamp`);
    const src = await frame.getAttribute("src");
    expect(src).toContain(id);
    expect(src).toContain("tracklist=true");
    expect(src).not.toContain("autoplay");
  }
  await expect(page.getByRole("link", { name: "Buy or support on Bandcamp" })).toHaveCount(EMBEDS.length);
});

test("the Music button does not load a player until it is opened", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Music" })).toBeVisible();
  await expect(page.locator("iframe[src*='bandcamp.com']")).toHaveCount(0);
});

test("the floating player defaults to INITIATES OF THE FLAME and stays mounted", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Music" }).click();
  const frame = page.locator("#ss-music-player iframe");
  await expect(frame).toHaveAttribute("src", /album=744084806/);
  await expect(frame).toHaveAttribute("src", /tracklist=true/);
  const src = await frame.getAttribute("src");
  expect(src).not.toContain("autoplay");
  await expect(page.getByLabel("Choose a release")).toHaveValue("744084806");
  await frame.evaluate((element) => {
    element.setAttribute("data-kept", "1");
  });

  await page.getByRole("link", { name: "South Africa" }).click();
  await expect(page).toHaveURL(/\/sa-careers/);
  await expect(page.locator("iframe[data-kept='1']")).toHaveCount(1);
  await expect(page.locator("iframe[data-kept='1']")).toHaveAttribute("src", /album=744084806/);

  await page.getByLabel("Choose a release").selectOption("3347381230");
  await expect(page.locator("#ss-music-player iframe")).toHaveAttribute("src", /album=3347381230/);
});

test("the Music button sits above the mobile tab bar", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  const button = page.getByRole("button", { name: "Music" });
  const nav = page.getByRole("navigation", { name: "Primary" });
  const buttonBox = await button.boundingBox();
  const navBox = await nav.boundingBox();
  expect(buttonBox).toBeTruthy();
  expect(navBox).toBeTruthy();
  expect(buttonBox!.x).toBeGreaterThanOrEqual(0);
  expect(buttonBox!.x + buttonBox!.width).toBeLessThanOrEqual(390);
  expect(buttonBox!.y + buttonBox!.height).toBeLessThanOrEqual(navBox!.y + 1);

  await button.click();
  const panel = page.locator("#ss-music-player");
  await expect(panel).toBeVisible();
  const panelBox = await panel.boundingBox();
  expect(panelBox).toBeTruthy();
  expect(panelBox!.x).toBeGreaterThanOrEqual(0);
  expect(panelBox!.x + panelBox!.width).toBeLessThanOrEqual(390);
  expect(panelBox!.y).toBeGreaterThanOrEqual(0);
  expect(panelBox!.y + panelBox!.height).toBeLessThanOrEqual(navBox!.y + 1);
});
