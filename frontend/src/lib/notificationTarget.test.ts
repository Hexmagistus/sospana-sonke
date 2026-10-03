import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { linkAttrs, notificationTarget, PREFERENCES_HREF } from "./notificationTarget";

const LISTING = "https://careers.example.com/jobs/42";

describe("notification targets", () => {
  it("opens a tagged listing in a new tab and refuses unsafe URLs", () => {
    const tagged = notificationTarget({ type: "admin_suggestion", link_url: LISTING });
    assert.deepEqual(tagged, { kind: "external", href: LISTING });
    assert.deepEqual(linkAttrs(tagged), { target: "_blank", rel: "noopener noreferrer" });

    const http = notificationTarget({ type: "admin_suggestion", link_url: "  http://jobs.example.com/a  " });
    assert.equal(http.kind, "external");
    assert.equal(http.href, "http://jobs.example.com/a");
    assert.deepEqual(linkAttrs(http), { target: "_blank", rel: "noopener noreferrer" });

    for (const bad of [
      "javascript:alert(1)",
      "JavaScript:alert(1)",
      "data:text/html,hi",
      "https://user:pass@careers.example.com/jobs",
      "https://careers.example.com/jobs\\evil",
      "//careers.example.com/jobs",
      "/\\careers.example.com",
      "vbscript:msgbox(1)",
    ]) {
      const target = notificationTarget({ type: "admin_suggestion", link_url: bad });
      assert.equal(target.kind, "internal", bad);
      assert.equal(target.href, "/notifications", bad);
      assert.deepEqual(linkAttrs(target), {}, bad);
    }
  });

  it("keeps in-app paths on this site and blocks path tricks", () => {
    const mention = notificationTarget({
      type: "mention",
      link_url: "/companies?company=abc-1",
    });
    assert.deepEqual(mention, { kind: "internal", href: "/companies?company=abc-1" });
    assert.deepEqual(linkAttrs(mention), {});

    const sneaky = notificationTarget({
      type: "mention",
      link_url: "/companies/../../admin",
    });
    assert.equal(sneaky.href, "/companies");

    const scriptPath = notificationTarget({
      type: "mention",
      link_url: "/companies?company=1javascript:alert(1)",
    });
    assert.equal(scriptPath.href, "/companies");
  });

  it("sends the preferences notice to the preferences page", () => {
    const fromAbsolute = notificationTarget({
      type: "consent_choices",
      link_url: "https://sospana-sonke.vercel.app/security#notification-preferences",
    });
    assert.deepEqual(fromAbsolute, { kind: "internal", href: PREFERENCES_HREF });
    assert.equal(PREFERENCES_HREF, "/security#notification-preferences");
    assert.deepEqual(linkAttrs(fromAbsolute), {});
  });

  it("routes each other notice to its page", () => {
    assert.deepEqual(
      notificationTarget({ type: "strong_match", related_id: "match-1" }),
      { kind: "internal", href: "/matches/match-1" },
    );
    assert.deepEqual(
      notificationTarget({ type: "action_required", related_id: "app-9" }),
      { kind: "internal", href: "/applications/app-9" },
    );
    assert.equal(notificationTarget({ type: "daily_agent_briefing" }).href, "/applications");
    assert.equal(notificationTarget({ type: "new_jobs" }).href, "/agent");
    assert.deepEqual(
      notificationTarget({ type: "report_ready", related_id: "rep-1" }),
      { kind: "download", href: "/reports/rep-1/download" },
    );
    assert.equal(
      notificationTarget({
        type: "link_updated",
        related_id: "550e8400-e29b-41d4-a716-446655440000:abc",
      }).href,
      "/companies?company=550e8400-e29b-41d4-a716-446655440000",
    );
    assert.equal(notificationTarget({ type: "source_alert" }).href, "/admin");
    assert.equal(
      notificationTarget({ type: "strong_match", related_id: "../admin" }).href,
      "/matches",
    );
  });

  it("prefers a real listing link over the generic page", () => {
    const match = notificationTarget({
      type: "strong_match",
      related_id: "match-1",
      link_url: LISTING,
    });
    assert.equal(match.kind, "external");
    assert.equal(match.href, LISTING);
  });
});
