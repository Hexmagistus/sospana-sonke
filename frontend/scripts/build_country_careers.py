"""Builds src/data/countryCareers.json: per-country careers links from backend/seed/company_database_import.csv,
using exactly the same rules and categories as build_sa_careers.py (static snapshot; no live DB needed).
Only countries on the public header list (directory-snapshot-visible.json) are written."""
import csv, json, re, os, collections, unicodedata
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
src = open(os.path.join(HERE, "build_sa_careers.py"), encoding="utf-8").read().split("items, skipped, seen")[0]
g = {"__file__": os.path.join(HERE, "build_sa_careers.py")}; exec(src, g)
abbr, CATS, ORDER = g["abbr"], dict(g["CATS"]), list(g["ORDER"])
def slug(n):
    f = "".join(c for c in unicodedata.normalize("NFD", n) if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", "-", f).strip("-") or "country"
snap = json.load(open(os.path.join(ROOT, "frontend/src/data/directory-snapshot-visible.json")))
wanted = {n for n, c in snap["by_country_with_link"].items() if c > 0 and n not in ("International", "Africa")}
items = collections.defaultdict(lambda: collections.defaultdict(list)); seen = collections.defaultdict(set)
for r in csv.DictReader(open(os.path.join(ROOT, "backend/seed/company_database_import.csv"), encoding="utf-8")):
    c = r["country"].strip()
    if c not in wanted: continue
    st = r["source_type"].upper().strip() or "PRIVATE"
    url = r["careers_url"].strip()
    s = (r["careers_status"] + " " + r["relevance_note"]).lower()
    if r["active"] != "true" or not url.startswith("http") or "homepage" in s or "no confirmed vacancies page" in s or "no live vacancies page" in s or "no public vacancies page" in s:
        continue
    key = url.rstrip("/").lower()
    if key in seen[c]: continue
    seen[c].add(key)
    if st not in CATS: CATS[st] = st.title()
    if st not in ORDER: ORDER.append(st)
    items[c][st].append({"a": abbr(r["company_name"], st), "n": r["company_name"], "u": url})
out = {}
for c in sorted(wanted):
    cats = [{"key": k, "name": CATS[k], "items": sorted(items[c][k], key=lambda x: (x["a"].lower(), x["n"].lower()))} for k in ORDER if items[c].get(k)]
    out[slug(c)] = {"name": c, "categories": cats}
json.dump(out, open(os.path.join(ROOT, "frontend/src/data/countryCareers.json"), "w"), ensure_ascii=False, separators=(",", ":"))
tot = {k: sum(len(x["items"]) for x in v["categories"]) for k, v in out.items()}
print("countries", len(out), "with links", sum(1 for v in tot.values() if v), "links", sum(tot.values()))
print("empty", [k for k, v in tot.items() if not v]); print(sorted(tot.items(), key=lambda x: -x[1]))
