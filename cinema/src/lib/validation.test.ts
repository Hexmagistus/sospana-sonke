import { describe, expect, it } from "vitest";
import { validateMovieDraft, validateTakedown } from "./validation";

describe("complaints and edits", () => {
  it("rejects a short complaint and an unknown title", () => {
    const result = validateTakedown({
      claimantName: "A",
      contactEmail: "not-an-email",
      contentId: "missing",
      reason: "too short",
      knownIds: ["sherlock-jr"],
    });
    expect(result.ok).toBe(false);
  });

  it("accepts a complete complaint", () => {
    const result = validateTakedown({
      claimantName: "Ada Lovelace",
      contactEmail: "ada@example.com",
      contentId: "sherlock-jr",
      reason: "This copy uses a soundtrack I own and it should be reviewed.",
      knownIds: ["sherlock-jr"],
    });
    expect(result.ok).toBe(true);
  });

  it("refuses playback without a licence URL", () => {
    const result = validateMovieDraft({
      title: "Example",
      description: "A real description of a film that is long enough.",
      releaseYear: 1924,
      country: "France",
      ageRating: "All",
      contentType: "movie",
      playbackUrl: "https://archive.org/embed/example",
      rightsVerified: true,
    });
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.errors.licenceEvidenceUrl).toBeTruthy();
  });
});
