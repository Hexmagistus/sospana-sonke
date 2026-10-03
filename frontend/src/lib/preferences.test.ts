import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { needsBanner, POST_TYPES, postTypeLabel, unchosenCount, yesNoLabel } from "./preferences";

describe("client preferences", () => {
  it("keeps not chosen apart from yes and no", () => {
    assert.equal(yesNoLabel("yes"), "Yes");
    assert.equal(yesNoLabel("no"), "No");
    assert.equal(yesNoLabel("not_chosen"), "Not chosen");
    assert.equal(yesNoLabel(undefined), "Not chosen");
    assert.equal(postTypeLabel(null), "Not chosen");
    assert.equal(postTypeLabel("none"), "Don't consider me for posts right now");
    assert.equal(postTypeLabel("bogus"), "Not chosen");
  });

  it("counts what is still unchosen", () => {
    assert.equal(unchosenCount(null), 0);
    assert.equal(unchosenCount({}), 3);
    assert.equal(
      unchosenCount({ tagging_state: "no", preferred_post_state: "chosen", alerts_state: "not_chosen" }),
      1,
    );
    assert.equal(
      unchosenCount({ tagging_state: "yes", preferred_post_state: "chosen", alerts_state: "no" }),
      0,
    );
  });

  it("shows the banner until all three are chosen, and never to a signed-out visitor or an admin", () => {
    assert.equal(needsBanner(null), false);
    assert.equal(needsBanner({ show_consent_banner: true }), true);
    assert.equal(needsBanner({ show_consent_banner: false, tagging_state: "not_chosen" }), false);
    assert.equal(needsBanner({ role: "admin" }), false);
    assert.equal(needsBanner({ role: "candidate", tagging_state: "yes", preferred_post_state: "chosen" }), true);
    assert.equal(
      needsBanner({ role: "candidate", tagging_state: "yes", preferred_post_state: "chosen", alerts_state: "no" }),
      false,
    );
  });

  it("lists the same post types the server accepts", () => {
    const values = POST_TYPES.map((p) => p.value);
    assert.deepEqual(values.slice(0, 2), ["any", "permanent"]);
    assert.ok(values.includes("none"));
    assert.equal(new Set(values).size, values.length);
  });
});
