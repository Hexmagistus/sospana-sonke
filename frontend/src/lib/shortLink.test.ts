import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { roleCode, roleIdFromCode, sharePlain, smsHref, whatsAppHref } from "./shortLink.js";

const id = "f2a26f43-00fa-4791-a16e-717c99af6c29";

describe("short role links", () => {
  it("turns a role id into 22 characters and back", () => {
    const code = roleCode(id);
    assert.ok(code);
    assert.equal(code.length, 22);
    assert.equal(roleIdFromCode(code), id);
    assert.equal(roleCode("not-a-role"), null);
    assert.equal(roleIdFromCode("https://evil.example"), null);
    assert.equal(roleIdFromCode("../admin"), null);
  });

  it("keeps a plain summary short and ends with the short link", () => {
    const text = sharePlain({
      title: "Senior Provisioning Officer",
      company_name: "Buffalo City TVET College",
      company_country: "South Africa",
      location: "East London",
      closing_date: "2026-10-28",
      application_url: "https://careers.example/jobs/1",
    }, "https://sospana-sonke.vercel.app/go/abc");
    assert.match(text, /Senior Provisioning Officer/);
    assert.match(text, /Buffalo City TVET College/);
    assert.match(text, /Apply: https:\/\/careers\.example\/jobs\/1/);
    assert.ok(text.endsWith("https://sospana-sonke.vercel.app/go/abc"));
    assert.ok(text.length < 480);
    const long = sharePlain({
      title: "A".repeat(200),
      company_name: "B".repeat(200),
      application_url: "https://example.com/" + "c".repeat(800),
    }, "https://sospana-sonke.vercel.app/go/abc");
    assert.ok(long.endsWith("https://sospana-sonke.vercel.app/go/abc"));
    assert.ok(long.length < 480);
    assert.match(whatsAppHref(text), /^https:\/\/wa\.me\/\?text=/);
    assert.match(smsHref(text), /^sms:\?&body=/);
  });
});
