"""Check every row in additions.py against the live source and record the result.

Writes data/additions-evidence.json. A row that fails any check is written with
"ok": false and a reason, and build_catalog.py leaves it out.

Internet Archive: reads https://archive.org/metadata/<id>, requires a licenseurl
that is a public-domain mark, CC0, CC BY or CC BY-SA (NC and ND are refused),
picks the playable file, and requests the embed and file URLs.

YouTube: requires the oEmbed endpoint to return 200, the public watch page to
report playability OK with playableInEmbed true, the uploading channel id to be
the rights holder's channel listed in additions.YT_HOLDERS, and the
youtube-nocookie embed URL to answer 200. Region availability is copied from
the watch page. No video is downloaded.

Usage: python3 scripts/verify_additions.py [--only slug,slug] [--workers 4]
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import additions  # noqa: E402

UA = "SospanaCinemaVerifier/1.0 (+catalogue licence check; contact via repository)"
EVIDENCE = ROOT / "data" / "additions-evidence.json"
REJECT = ("by-nc", "by-nd", "nc-sa", "nc-nd")
TODAY = dt.date.today().isoformat()

# Names used by src/lib/countries.ts where they differ from ISO short names.
NAME_OVERRIDES = {
    "TZ": "Tanzania", "CD": "Democratic Republic of the Congo", "CG": "Congo", "CI": "Côte d'Ivoire", "CV": "Cape Verde",
    "ST": "São Tomé and Príncipe", "SZ": "Eswatini", "RU": "Russia", "KR": "South Korea", "KP": "North Korea", "TW": "Taiwan",
    "VN": "Vietnam", "LA": "Laos", "BO": "Bolivia", "IR": "Iran", "SY": "Syria", "MD": "Moldova", "VE": "Venezuela",
    "BN": "Brunei", "FM": "Micronesia", "VA": "Vatican City", "GB": "United Kingdom", "US": "United States", "MO": "Macau",
    "HK": "Hong Kong", "PS": "Palestine", "TL": "Timor-Leste", "GM": "Gambia",
}


def http(url: str, method: str = "GET", tries: int = 3, rng: bool = False) -> tuple[int, str, str]:
    """Return (status, final_url, body-or-empty)."""
    last = (0, url, "")
    for attempt in range(tries):
        headers = {"User-Agent": UA if "youtube" not in url else "Mozilla/5.0", "Accept-Language": "en"}
        if rng:
            headers["Range"] = "bytes=0-1023"
        req = urllib.request.Request(url, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=60) as h:
                body = h.read(4_000_000 if not rng else 1024)
                return h.status, h.geturl(), body.decode("utf-8", "replace") if not rng else ""
        except urllib.error.HTTPError as e:
            last = (e.code, url, "")
            if e.code in (404, 410, 401, 403):
                return last
        except Exception as e:  # timeouts, resets
            last = (0, url, repr(e)[:200])
        time.sleep(2 * (attempt + 1))
    return last


def licence_kind(url: str | None) -> str | None:
    if not url:
        return None
    v = url.strip().lower()
    if not v.startswith(("http://", "https://")) or any(p in v for p in REJECT):
        return None
    if "publicdomain/zero" in v:
        return "cc0"
    if "publicdomain/mark" in v:
        return "public-domain-mark"
    if "/licenses/publicdomain" in v:
        return "public-domain"
    m = re.search(r"/licenses/(by-sa|by)/([0-9.]+)", v)
    if m:
        return f"cc-{m.group(1)}-{m.group(2)}"
    return None


def seconds(value) -> int:
    if value is None:
        return 0
    text = str(value).strip()
    try:
        return int(float(text))
    except ValueError:
        pass
    parts = [p for p in re.split(r"[:']", text) if p.strip().isdigit()]
    if len(parts) >= 2:
        total = 0
        for p in parts:
            total = total * 60 + int(p)
        return total
    return 0


def pick_file(files: list[dict], wanted: str | None) -> dict | None:
    videos = [f for f in files if f.get("name", "").lower().endswith(".mp4")]
    if wanted:
        return next((f for f in videos if f["name"] == wanted), None)
    small = [f for f in videos if f["name"].endswith("_512kb.mp4")]
    if small:
        return small[0]
    sized = sorted((f for f in videos if int(f.get("size") or 0) and int(f["size"]) < 900_000_000), key=lambda f: int(f["size"]))
    return sized[0] if sized else None


def check_ia(row: dict) -> dict:
    ident = row["identifier"]
    out = {"kind": "internet-archive", "identifier": ident, "checkedAt": TODAY, "ok": False}
    status, _, body = http(f"https://archive.org/metadata/{ident}")
    out["metadataStatus"] = status
    if status != 200 or not body.strip().startswith("{"):
        out["reason"] = f"metadata request returned {status}"
        return out
    data = json.loads(body)
    meta = data.get("metadata") or {}
    lic = meta.get("licenseurl")
    out["licenseurl"] = lic
    out["rights"] = meta.get("rights")
    out["sourceTitle"] = meta.get("title")
    out["sourceDate"] = meta.get("date") or meta.get("year")
    kind = licence_kind(lic)
    if not kind:
        out["reason"] = f"licenseurl {lic!r} is not an allowed open licence"
        return out
    out["licenceType"] = kind
    chosen = pick_file(data.get("files") or [], row.get("file"))
    if row.get("file") and not chosen:
        out["reason"] = f"file {row['file']!r} not on the item"
        return out
    embed = f"https://archive.org/embed/{ident}" + (f"/{urllib.parse.quote(row['file'])}" if row.get("file") else "")
    st, _, _ = http(embed)
    out["embedUrl"], out["embedStatus"] = embed, st
    if st != 200:
        out["reason"] = f"embed returned {st}"
        return out
    runtime = 0
    if chosen:
        url = f"https://archive.org/download/{ident}/{urllib.parse.quote(chosen['name'], safe='')}"
        fst, final, _ = http(url, rng=True)
        out["fileUrl"], out["fileStatus"], out["fileHost"] = url, fst, urllib.parse.urlparse(final).netloc
        if fst in (200, 206):
            out["file"] = chosen["name"]
            out["fileBytes"] = int(chosen.get("size") or 0)
        else:
            out["fileUrl"] = None
        runtime = seconds(chosen.get("length"))
    runtime = runtime or seconds(meta.get("runtime"))
    if runtime <= 0:
        out["reason"] = "no runtime on the item"
        return out
    out["runtimeSeconds"] = runtime
    out["ok"] = True
    return out


def country_names(codes: list[str]) -> list[str]:
    try:
        import pycountry  # dev-only helper
    except ImportError:  # pragma: no cover
        pycountry = None
    names = []
    for code in codes:
        if code in NAME_OVERRIDES:
            names.append(NAME_OVERRIDES[code])
            continue
        c = pycountry.countries.get(alpha_2=code) if pycountry else None
        names.append(getattr(c, "common_name", None) or getattr(c, "name", None) or code)
    return sorted(set(names))


def check_yt(row: dict) -> dict:
    vid = row["vid"]
    holder = additions.YT_HOLDERS[row["holder"]]
    out = {"kind": "youtube", "videoId": vid, "checkedAt": TODAY, "ok": False, "expectedChannelId": holder[1]}
    watch = f"https://www.youtube.com/watch?v={vid}"
    st, _, body = http("https://www.youtube.com/oembed?format=json&url=" + urllib.parse.quote(watch))
    out["oembedStatus"] = st
    if st != 200:
        out["reason"] = f"oEmbed returned {st}"
        return out
    o = json.loads(body)
    out["oembedAuthor"], out["oembedAuthorUrl"] = o.get("author_name"), o.get("author_url")
    player = {}
    for attempt in range(4):
        st, _, page = http(watch)
        m = re.search(r"ytInitialPlayerResponse\s*=\s*(\{.+?\});\s*(?:var|</script>)", page or "")
        player = json.loads(m.group(1)) if m else {}
        if (player.get("playabilityStatus") or {}).get("status") == "OK":
            break
        time.sleep(5 + 5 * attempt)
    ps = player.get("playabilityStatus") or {}
    vd = player.get("videoDetails") or {}
    mf = (player.get("microformat") or {}).get("playerMicroformatRenderer") or {}
    out.update(
        watchStatus=st, playability=ps.get("status"), playabilityReason=ps.get("reason"), playableInEmbed=ps.get("playableInEmbed"),
        sourceTitle=vd.get("title"), channelId=vd.get("channelId"), channelName=vd.get("author"), uploadDate=mf.get("uploadDate") or mf.get("publishDate"),
        runtimeSeconds=int(vd.get("lengthSeconds") or 0), familySafe=mf.get("isFamilySafe"), isLive=vd.get("isLiveContent"),
        sourceDescription=(vd.get("shortDescription") or "")[:1500],
    )
    regions = mf.get("availableCountries") or []
    if not regions:
        rg = re.search(r'itemprop="regionsAllowed" content="([^"]*)"', page or "")
        regions = rg.group(1).split(",") if rg else []
    out["regionCodes"] = sorted(regions)
    if ps.get("status") != "OK":
        out["reason"] = f"watch page playability {ps.get('status')}: {ps.get('reason')}"
        return out
    if ps.get("playableInEmbed") is not True:
        out["reason"] = "embedding switched off"
        return out
    if vd.get("channelId") != holder[1]:
        out["reason"] = f"uploaded by {vd.get('channelId')} ({vd.get('author')}), not the rights holder channel {holder[1]}"
        return out
    if out["runtimeSeconds"] <= 0 or vd.get("isLiveContent"):
        out["reason"] = "no runtime or a live stream"
        return out
    embed = f"https://www.youtube-nocookie.com/embed/{vid}"
    est, _, _ = http(embed)
    out["embedUrl"], out["embedStatus"] = embed, est
    if est != 200:
        out["reason"] = f"embed returned {est}"
        return out
    if len(regions) >= 240 or not regions:
        out["territories"] = ["WORLD"]
    else:
        out["territories"] = country_names(regions)
    out["ok"] = True
    return out


def key(row: dict) -> str:
    return row.get("slug") or "yt:" + row["vid"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--failed", action="store_true", help="re-check only rows that failed last time")
    args = ap.parse_args()
    current = json.loads(EVIDENCE.read_text()) if EVIDENCE.exists() else {}
    rows = [("ia", r) for r in additions.IA] + [("yt", r) for r in additions.YT]
    only = {s for s in args.only.split(",") if s}
    if only:
        rows = [(k, r) for k, r in rows if key(r) in only]
    if args.failed:
        rows = [(k, r) for k, r in rows if not current.get(key(r), {}).get("ok")]

    def run(item):
        kind, row = item
        try:
            return key(row), (check_ia(row) if kind == "ia" else check_yt(row))
        except Exception as e:  # keep going, record the error
            return key(row), {"ok": False, "reason": f"checker error {e!r}"[:300], "checkedAt": TODAY}

    with cf.ThreadPoolExecutor(args.workers) as ex:
        for k, res in ex.map(run, rows):
            current[k] = res
            print(("OK  " if res.get("ok") else "FAIL"), k, res.get("reason", ""), flush=True)
    EVIDENCE.write_text(json.dumps(dict(sorted(current.items())), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    ok = sum(1 for v in current.values() if v.get("ok"))
    print(f"evidence rows {len(current)}, passing {ok}")


if __name__ == "__main__":
    main()
