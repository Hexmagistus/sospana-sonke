import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, it } from "node:test";
import { cacheRoleMessage, readOfflineRoles, rememberOfflineRole, roleCachePath } from "./offlineCache.js";

const id = "f2a26f43-00fa-4791-a16e-717c99af6c29";

describe("offline role cache", () => {
  it("caches only a public role page", () => {
    assert.equal(roleCachePath(id), `/jobs/${id}`);
    assert.equal(roleCachePath("../saved-opportunities"), null);
    assert.equal(roleCachePath("not-a-role"), null);
    assert.deepEqual(cacheRoleMessage(id), { type: "cache-role", url: `/jobs/${id}` });
    assert.equal(cacheRoleMessage("https://evil.example/jobs"), null);
  });

  it("keeps eight titles and drops a row with no title", () => {
    let rows: unknown[] = [];
    for (let index = 0; index < 10; index += 1) {
      const roleId = `00000000-0000-4000-8000-${String(index).padStart(12, "0")}`;
      rows = rememberOfflineRole(rows, { id: roleId, title: `Role ${index}`, company: "Example" });
    }
    assert.equal(readOfflineRoles(rows).length, 8);
    assert.equal(readOfflineRoles(rows)[0].title, "Role 9");
    assert.equal(rememberOfflineRole(rows, { id, title: "  ", company: "Example" }).length, 8);
  });

  it("asks the service worker for public pages only, and the offline page lists stored titles", () => {
    const worker = readFileSync(resolve(process.cwd(), "public/sw.js"), "utf8");
    const page = readFileSync(resolve(process.cwd(), "public/offline.html"), "utf8");
    assert.match(worker, /v4/);
    assert.match(worker, /cache-role/);
    assert.match(worker, /ROLE_PAGE/);
    assert.equal(worker.includes("saved-opportunities"), false);
    assert.match(page, /ss-recent-roles/);
    assert.match(page, /ss-offline-roles/);
    assert.match(page, /textContent/);
  });
});
