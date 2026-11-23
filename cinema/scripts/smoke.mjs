import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

const base = process.env.CINEMA_BASE || "http://127.0.0.1:3456";
const out = process.env.CINEMA_ARTIFACTS || "/opt/cursor/artifacts";
mkdirSync(out, { recursive: true });

const browser = await chromium.launch({ headless: true });
const failures = [];

function check(name, ok, detail) {
  if (!ok) failures.push(`${name}: ${detail}`);
  else console.log("ok", name);
}

for (const [width, height, tag] of [
  [1280, 800, "desktop"],
  [390, 844, "mobile"],
]) {
  const page = await browser.newPage({ viewport: { width, height } });
  page.setDefaultTimeout(25000);
  await page.goto(base + "/", { waitUntil: "networkidle" });
  await page.getByRole("heading", { level: 1, name: "Sherlock Jr." }).waitFor();
  await page.screenshot({ path: `${out}/cinema-home-${tag}.png` });
  check(`${tag} home anime row`, (await page.getByRole("heading", { level: 2, name: "Anime", exact: true }).count()) === 1 && (await page.locator('main a[href="/movies/black-clover-e1"]').count()) > 0, "Anime row missing on home");

  await page.goto(base + "/categories/anime", { waitUntil: "networkidle" });
  check(`${tag} anime shelf filled`, (await page.locator('a[href="/movies/mobile-suit-gundam-e1"]').count()) > 0 && (await page.getByTestId("empty-category").count()) === 0, "anime shelf empty");
  await page.screenshot({ path: `${out}/cinema-anime-${tag}.png` });
  await page.goto(base + "/watch/black-clover-e1", { waitUntil: "domcontentloaded" });
  check(`${tag} anime embed`, (await page.getByTestId("player-embed").getAttribute("src")) === "https://www.youtube-nocookie.com/embed/JxpVIn26nfk", "anime embed missing");

  await page.goto(base + "/categories/classic-cinema", { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "Classic Cinema" }).waitFor();
  await page.screenshot({ path: `${out}/cinema-classic-${tag}.png` });

  await page.goto(base + "/categories/african-cinema", { waitUntil: "networkidle" });
  check(`${tag} african shelf filled`, (await page.locator('a[href="/movies/october-1"]').count()) > 0, "October 1 missing from African Cinema");
  await page.screenshot({ path: `${out}/cinema-african-${tag}.png` });

  await page.goto(base + "/categories/south-african-movies", { waitUntil: "networkidle" });
  check(`${tag} south africa filled`, (await page.locator('a[href="/movies/hopeville"]').count()) > 0 && (await page.getByTestId("empty-category").count()) === 0, "Hopeville missing");

  await page.goto(base + "/watch/hopeville", { waitUntil: "domcontentloaded" });
  check(`${tag} youtube embed`, (await page.getByTestId("player-embed").getAttribute("src")) === "https://www.youtube-nocookie.com/embed/3yQW0YYhtg0", "official embed missing");

  await page.goto(base + "/kids", { waitUntil: "networkidle" });
  check(`${tag} pending kids hidden`, !(await page.locator("main").innerHTML()).includes("/movies/ubongo-kids-") && !(await page.locator("main").innerHTML()).includes("/movies/pokemon-horizons-"), "a pending kids title appeared in Kids Cinema");

  await page.goto(base + "/search?q=sherlok", { waitUntil: "networkidle" });
  await page.getByTestId("search-correction").waitFor();
  check(`${tag} typo search`, (await page.getByRole("link", { name: "Sherlock Jr." }).count()) > 0, "no sherlock result");
  await page.screenshot({ path: `${out}/cinema-search-${tag}.png` });

  await page.goto(base + "/movies/nosferatu", { waitUntil: "networkidle" });
  await page.getByTestId("watch-now").waitFor();
  await page.screenshot({ path: `${out}/cinema-detail-${tag}.png` });

  await page.goto(base + "/watch/caminandes-llama-drama", { waitUntil: "domcontentloaded" });
  await page.getByTestId("player-video").waitFor();
  await page.getByTestId("player-play").click();
  await page.waitForFunction(() => {
    const video = document.querySelector("[data-testid=player-video]");
    return video && video.currentTime > 0.2 && video.readyState >= 2;
  });
  await page.screenshot({ path: `${out}/cinema-player-${tag}.png` });
  await page.goto(base + "/library", { waitUntil: "networkidle" });
  check(`${tag} resume saved`, (await page.getByTestId("library-continue").innerText()).includes("Llama"), "continue watching missing");

  await page.goto(base + "/watch/metropolis", { waitUntil: "domcontentloaded" });
  check(`${tag} embed player`, (await page.getByTestId("player-embed").getAttribute("src"))?.includes("archive.org/embed/"), "embed missing");

  await page.goto(base + "/kids", { waitUntil: "networkidle" });
  const kidsHtml = await page.locator("main").innerHTML();
  check(`${tag} kids gate`, !kidsHtml.includes("/movies/sintel") && kidsHtml.includes("Llama Drama"), "kids shelf linked a rejected title or hid an approved one");
  await page.screenshot({ path: `${out}/cinema-kids-${tag}.png` });

  await page.goto(base + "/movies/big-buck-bunny", { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "Save Big Buck Bunny on this device" }).click();
  await page.goto(base + "/library", { waitUntil: "networkidle" });
  await page.getByRole("link", { name: "Big Buck Bunny" }).waitFor();
  await page.screenshot({ path: `${out}/cinema-library-${tag}.png` });
  await page.getByTestId("clear-local").click();
  await page.getByText("No favourites saved on this device.").waitFor();
  check(`${tag} cleared`, !(await page.locator("main").innerText()).includes("Big Buck Bunny"), "favourite remained");

  if (tag === "desktop") {
    await page.goto(base + "/takedown", { waitUntil: "networkidle" });
    await page.screenshot({ path: `${out}/cinema-takedown-${tag}.png` });
    await page.locator("input[name=claimantName]").fill("Ada Lovelace");
    await page.locator("input[name=contactEmail]").fill("ada@example.com");
    await page.locator("select[name=contentId]").selectOption("sherlock-jr");
    await page.locator("textarea[name=reason]").fill("Please review this archive copy. I believe the soundtrack is not cleared.");
    await page.getByTestId("takedown-submit").click();
    await page.getByTestId("takedown-success").waitFor();

    await page.goto(base + "/admin/login", { waitUntil: "networkidle" });
    await page.getByTestId("admin-email").fill(process.env.ADMIN_EMAIL || "demo-admin@sospana-cinema.local");
    await page.getByTestId("admin-password").fill(process.env.ADMIN_PASSWORD || "demo-cinema-change-me");
    await page.getByTestId("admin-submit").click();
    await page.getByTestId("admin-dashboard").waitFor();
    await page.screenshot({ path: `${out}/cinema-admin-${tag}.png` });
    await page.goto(base + "/admin/takedowns", { waitUntil: "networkidle" });
    check("takedown stored", (await page.locator("main").innerText()).includes("sherlock-jr"), "complaint missing");
    await page.screenshot({ path: `${out}/cinema-admin-takedowns.png` });
  } else {
    await page.goto(base + "/takedown", { waitUntil: "networkidle" });
    await page.screenshot({ path: `${out}/cinema-takedown-${tag}.png` });
    await page.goto(base + "/admin/login", { waitUntil: "networkidle" });
    await page.getByTestId("admin-email").fill(process.env.ADMIN_EMAIL || "demo-admin@sospana-cinema.local");
    await page.getByTestId("admin-password").fill(process.env.ADMIN_PASSWORD || "demo-cinema-change-me");
    await page.getByTestId("admin-submit").click();
    await page.getByTestId("admin-dashboard").waitFor();
    await page.screenshot({ path: `${out}/cinema-admin-${tag}.png` });
  }
  await page.close();
}

const sitemap = await fetch(base + "/sitemap.xml");
const sitemapText = await sitemap.text();
check("sitemap", sitemap.ok && sitemapText.includes("/movies/sherlock-jr") && sitemapText.includes("/kids"), sitemap.status + " " + sitemapText.slice(0, 120));
const robots = await fetch(base + "/robots.txt");
const robotsText = await robots.text();
check("robots", robots.ok && robotsText.includes("Disallow: /admin") && robotsText.includes("sitemap.xml"), robotsText);

await browser.close();
if (failures.length) {
  console.error(failures.join("\n"));
  process.exit(1);
}
console.log("smoke passed");
