"""Builds src/data/saCareers.json from backend/seed/company_database_import.csv (South Africa only).
Temporary maintenance-mode directory. Only active rows with a real careers_url are kept; homepage fallbacks are skipped."""
import csv, json, re, os, collections
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CATS = {"JSE":"JSE-listed companies","PRIVATE":"Private companies","SOE":"State-owned entities","DEPT":"Government departments",
 "MUNI":"Municipalities","UNI":"Universities","COLLEGE":"Colleges","SETA":"SETAs","HOSPITAL":"Hospitals","NGO":"NGOs",
 "FED":"Regulators & councils","SPORT":"Sport","MUSIC":"Music & arts"}
ORDER = ["DEPT","SOE","MUNI","UNI","COLLEGE","SETA","HOSPITAL","JSE","PRIVATE","NGO","FED","SPORT","MUSIC"]
SUF = re.compile(r"\b(Group|Holdings|Limited|Ltd|Proprietary|Pty|Company|Corporation|Incorporated|Inc|plc|SOC|Properties|\(Pty\))\b\.?", re.I)
INIT = {"DEPT","SOE","SETA","FED","SPORT","UNI"}
SMALL = {"of","and","the","for","in","on","&"}
MUNI = [("Metropolitan Municipality","Metro"),("District Municipality","DM"),("Local Municipality","LM"),("Municipality","Mun.")]
def abbr(name, st):
    m = [p for p in re.findall(r"\(([^()]+)\)", name) if len(p) <= 14 and not re.search(r"\b(South|Pty|SOC|Ltd)\b", p)]
    if m: return m[-1].strip()
    base = re.sub(r"\([^)]*\)", "", name).strip()
    if base.isupper() and len(base) <= 14: return base
    for a, b in MUNI:
        if base.endswith(a): return base[: -len(a)].strip() + " " + b
    short = re.sub(r"\s+", " ", SUF.sub("", base)).strip(" ,-&")
    words = short.split()
    if st in INIT and len(words) >= 3:
        return "".join(w[0].upper() for w in words if w.lower() not in SMALL and w[0].isalpha())
    return short if len(short) <= 22 else " ".join(short.split()[:3])
items, skipped, seen = collections.defaultdict(list), collections.Counter(), set()
for r in csv.DictReader(open(os.path.join(ROOT, "backend/seed/company_database_import.csv"), encoding="utf-8")):
    if r["country"] != "South Africa": continue
    st = r["source_type"].upper()
    url = r["careers_url"].strip()
    s = (r["careers_status"] + " " + r["relevance_note"]).lower()
    if r["active"] != "true" or not url.startswith("http") or "homepage" in s or "no confirmed vacancies page" in s or "no live vacancies page" in s or "no public vacancies page" in s:
        skipped[st] += 1; continue
    key = url.rstrip("/").lower()
    if key in seen: skipped[st] += 1; continue
    seen.add(key)
    items[st].append({"a": abbr(r["company_name"], st), "n": r["company_name"], "u": url})
out = [{"key": k, "name": CATS[k], "items": sorted(items[k], key=lambda x: (x["a"].lower(), x["n"].lower()))} for k in ORDER if items.get(k)]
json.dump({"categories": out, "skipped": sum(skipped.values())}, open(os.path.join(ROOT, "frontend/src/data/saCareers.json"), "w"), ensure_ascii=False, separators=(",", ":"))
print({c["name"]: len(c["items"]) for c in out}, "links", sum(len(c["items"]) for c in out), "skipped", dict(skipped), sum(skipped.values()))
