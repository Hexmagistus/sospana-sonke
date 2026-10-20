"""Writes src/data/directory-snapshot-visible.json: the 2026-10-12 snapshot limited to the
countries in src/lib/visibleCountries.ts. The original snapshot is left untouched."""
import json, os, re
D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ts = open(os.path.join(D, "src/lib/visibleCountries.ts"), encoding="utf-8").read()
names = set()
for block in re.findall(r"export const (?:SADC_MEMBERS|BRICS_MEMBERS|ENGLISH_OFFICIAL) = \[(.*?)\] as const", ts, re.S):
    names |= set(re.findall(r'"([^"]+)"', block))
names |= {"Africa", "International"}
snap = json.load(open(os.path.join(D, "src/data/directory-snapshot.json"), encoding="utf-8"))
bc = {k: v for k, v in snap["by_country"].items() if k in names}
bl = {k: v for k, v in snap["by_country_with_link"].items() if k in names}
buckets = {"Africa", "International"}
hidden = sorted(set(snap["by_country"]) - names)
out = dict(snap)
out.update({
    "source": snap["source"] + " Trimmed to the visible countries (src/lib/visibleCountries.ts); hidden: " + ", ".join(hidden) + ".",
    "employers": sum(bc.values()), "countries": sum(1 for k in bc if k not in buckets),
    "by_country": bc, "with_link": sum(bl.values()),
    "countries_with_link": sum(1 for k, v in bl.items() if k not in buckets and v > 0), "by_country_with_link": bl,
})
json.dump(out, open(os.path.join(D, "src/data/directory-snapshot-visible.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("kept", out["countries"], "hidden", len(hidden), "employers", snap["employers"], "->", out["employers"],
      "with_link", snap["with_link"], "->", out["with_link"])
print("HIDDEN:", hidden)
print("KEPT:", sorted(k for k in bc if k not in buckets))
print("missing from snapshot:", sorted(names - set(snap["by_country"])))
