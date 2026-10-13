import assert from "node:assert/strict";
import { readFileSync, statSync } from "node:fs";
import { resolve } from "node:path";
import { describe, it } from "node:test";
import {
  AMBIENT_SRC,
  mayLoadAmbient,
  musicClickAction,
  readChoice,
  shouldPlayAmbient,
  uiSoundAllowed,
  writeChoice,
} from "./soundPrefs.js";

describe("soundtrack choices", () => {
  it("stays off until the stored value is the word on", () => {
    const bag = new Map<string, string>();
    const storage = {
      getItem: (key: string) => bag.get(key) ?? null,
      setItem: (key: string, value: string) => {
        bag.set(key, value);
      },
    };
    assert.equal(readChoice(storage, "ss-music"), false);
    assert.equal(readChoice(null, "ss-music"), false);
    writeChoice(storage, "ss-music", true);
    assert.equal(readChoice(storage, "ss-music"), true);
    writeChoice(storage, "ss-music", false);
    assert.equal(bag.get("ss-music"), "off");
  });

  it("starts on the first press and stops on the next, and never plays while hidden or on Data Saver", () => {
    assert.equal(musicClickAction(false), "play");
    assert.equal(musicClickAction(true), "stop");
    assert.equal(mayLoadAmbient(false), true);
    assert.equal(mayLoadAmbient(true), false);
    assert.equal(shouldPlayAmbient(true, false, false), true);
    assert.equal(shouldPlayAmbient(true, true, false), false);
    assert.equal(shouldPlayAmbient(false, false, false), false);
    assert.equal(shouldPlayAmbient(true, false, true), false);
  });

  it("keeps UI sounds off unless the sounds choice is on and motion is allowed", () => {
    assert.equal(uiSoundAllowed(false, false), false);
    assert.equal(uiSoundAllowed(true, true), false);
    assert.equal(uiSoundAllowed(true, false), true);
  });

  it("ships a small looped file with a CC0 record, and does not preload it from the shell", () => {
    assert.equal(AMBIENT_SRC, "/audio/ambient.ogg");
    const ogg = statSync(resolve(process.cwd(), "public/audio/ambient.ogg"));
    assert.ok(ogg.size < 300 * 1024, `ambient.ogg is ${ogg.size} bytes`);
    assert.ok(ogg.size > 1000);
    const licence = readFileSync(resolve(process.cwd(), "public/audio/LICENCE.txt"), "utf8");
    assert.match(licence, /CC0 1\.0/);
    const player = readFileSync(resolve(process.cwd(), "src/lib/ambientPlayer.ts"), "utf8");
    assert.match(player, /preload = "none"/);
    assert.match(player, /loop = true/);
    assert.match(player, /visibilitychange/);
    assert.equal(player.includes("autoplay"), false);
    const layout = readFileSync(resolve(process.cwd(), "src/app/layout.tsx"), "utf8");
    const home = readFileSync(resolve(process.cwd(), "src/components/home/HomeExperience.tsx"), "utf8");
    assert.equal(layout.includes("ambient.ogg"), false);
    assert.equal(home.includes("ambient.ogg"), false);
    assert.equal(layout.includes("<audio"), false);
  });
});
