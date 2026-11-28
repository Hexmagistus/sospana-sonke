"""Builds public/company-index.json for the company picker (homepage + /jobs).

Static, so the picker works when the database/API is offline. Source: the bundled
directory files src/data/countryCareers.json (all countries) and src/data/saCareers.json
(South Africa), plus a count of posts per employer in src/data/opportunitiesToday.json.
Run from frontend/:  python3 scripts/build_company_index.py
"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "src", "data")

def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

STOP = r"\b(the|limited|ltd|pty|group|holdings|company|co|plc|inc|soc|of|south africa|sa)\b"
def norm(s):
    s = re.sub(r"\(.*?\)", " ", s.lower()).replace("&", " and ")
    s = re.sub(STOP, " ", s)
    return re.sub(r"[^a-z0-9]+", "", s)

cc = json.load(open(os.path.join(DATA, "countryCareers.json")))
sa = json.load(open(os.path.join(DATA, "saCareers.json")))
ot = json.load(open(os.path.join(DATA, "opportunitiesToday.json")))

posts = {}
for p in ot["posts"]:
    e = p["employer"]
    posts.setdefault(e, 0)
    posts[e] += 1
by_norm = {}
for e in posts:
    for k in {norm(e), norm(re.sub(r"\(.*?\)", "", e)), norm((re.search(r"\((.*?)\)", e) or [None, ""])[1] or "")}:
        if len(k) >= 3:
            by_norm.setdefault(k, e)

# Directory name -> employer name used on /opportunities-today, where they differ.
ALIAS = {"Pick n Pay Stores": "Pick n Pay", "EOH Holdings": "iOCO", "Impala Platinum Holdings": "Implats"}
rows, seen = [], set()
def add(country, cat, it):
    key = (country, it["n"].lower())
    if key in seen or not it.get("u"):
        return
    seen.add(key)
    row = {"n": it["n"], "c": country, "k": cat, "u": it["u"]}
    cand = [norm(ALIAS.get(it["n"], it["n"]))]
    if country == "South Africa":
        for k in cand:
            if k in by_norm:
                e = by_norm[k]
                row["p"] = posts[e]
                row["a"] = slug(e)
                break
    rows.append(row)

for cat in sa["categories"]:
    for it in cat["items"]:
        add("South Africa", cat["name"], it)
for v in cc.values():
    for cat in v["categories"]:
        for it in cat["items"]:
            add(v["name"], cat["name"], it)

rows.sort(key=lambda r: (r["c"] != "South Africa", r["c"], r["n"].lower()))
out = os.path.join(HERE, "..", "public", "company-index.json")
json.dump({"count": len(rows), "companies": rows}, open(out, "w"), ensure_ascii=False, separators=(",", ":"))
print(len(rows), "companies;", sum(1 for r in rows if r.get("p")), "with posts on /opportunities-today")
