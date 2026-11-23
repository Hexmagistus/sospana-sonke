"""Turn additions.py rows plus their live evidence into catalogue rows.

A row is used only when data/additions-evidence.json has "ok": true for it.
Runtime, licence URL, file name, region list and the source's own title and
description come from that evidence, not from hand-typed values.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import quote

import additions

SERIES_NAMES = {
    "ubongo": "Ubongo Kids",
    "akili-and-me": "Akili and Me",
    "tinga-tinga": "Tinga Tinga Tales",
    "bino-and-fino": "Bino and Fino",
    "supa-strikas": "Supa Strikas",
}

JUNK = re.compile(r"(?i)^(subscribe|catch |after all|new 4k|produced by|\[rated|what is|gundam\.info|get ready|it's the moment|listen to|birthday party)")

PENDING_NOTE = (
    "Pending manual review, recorded {date}. Suggested age group to check: {group}. "
    "Not shown in Kids Cinema until a person watches it and approves it."
)


def slugify(text: str) -> str:
    text = re.sub(r"[’']", "", text.lower().replace("&", " and "))
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-")[:90]


def strip_symbols(text: str) -> str:
    text = "".join(ch for ch in text if (ord(ch) < 0x2190 or 0x3000 <= ord(ch) < 0xFF00) and ch not in "•▼")
    return re.sub(r"\s+", " ", text).strip(" -|:")


def episode_title(holder: str, source_title: str) -> str:
    series = SERIES_NAMES[holder]
    t = strip_symbols(source_title)
    if holder == "supa-strikas":
        parts = [p.strip() for p in t.split("|")]
        name = parts[1] if len(parts) > 1 else parts[0]
    elif holder == "bino-and-fino":
        m = re.search(r"Full Episode\s+(\d+)", t)
        name = re.split(r"\s*:?\s*Bino\s*(?:and|&)\s*Fino", t)[0].strip(" :")
        return f"{series} E{m.group(1)}: {name}" if m else f"{series}: {name}"
    else:
        name = t.split("|")[0].strip()
    name = re.sub(r"^(Full Episode\s*#?\d*\s*:|EPISODE\s*\d+\s*:)\s*", "", name, flags=re.I).strip()
    return f"{series}: {name}"


def first_paragraph(text: str, limit: int = 320) -> str:
    text = (text or "").replace("\r", "")
    para = next((p.strip() for p in text.split("\n\n") if len(p.strip()) > 40 and "http" not in p[:30]), "")
    para = re.sub(r"https?://\S+", "", para)
    para = re.sub(r"#\w+", "", para)
    para = re.split(r"(?i)\bif you (love|are looking)\b", para)[0]
    para = re.sub(r"\s+", " ", para).strip()
    if len(para) > limit:
        cut = para[:limit]
        stop = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
        para = cut[: stop + 1] if stop > 80 else cut.rsplit(" ", 1)[0] + "…"
    return para


def pending_review(group: str, date: str) -> dict:
    return {"status": "pending", "suitability": group, "notes": PENDING_NOTE.format(date=date, group=group), "reviewedAt": date}


def base_row(slug, title, description, year, runtime, genres, language, country, director, cast, ctype, age, poster, cats, note, sources, review, created):
    return dict(
        slug=slug, title=title, description=description, releaseYear=year, runtimeSeconds=runtime, genres=genres, language=language,
        country=country, director=director, cast=cast, contentType=ctype, ageRating=age, posterUrl=poster, backdropUrl=poster,
        trailerUrl=None, categories=cats, featured=False, published=True, createdAt=created + "T12:00:00Z",
        updatedAt=created + "T12:00:00Z", archiveIdentifier=None, note=note, sources=sources, review=review,
    )


def ia_rows(evidence: dict) -> list[dict]:
    rows = []
    for r in additions.IA:
        ev = evidence.get(r["slug"])
        if not ev or not ev.get("ok"):
            continue
        ident = r["identifier"]
        lic_type, lic_url = ev["licenceType"], ev["licenseurl"]
        record = f"https://archive.org/details/{ident}"
        common = dict(
            providerSlug="internet-archive", licenceType=lic_type, licenceEvidenceUrl=lic_url, sourceRecordUrl=record,
            licenceTerritories=["WORLD"], rightsVerified=True, playbackStatus="available", lastVerifiedAt=ev["checkedAt"],
            rightsHolder="Public domain or open licence per the source record", rightsHolderSource="internet-archive", subtitles=[],
        )
        sources = []
        if ev.get("fileUrl"):
            sources.append(dict(common, playbackType="mp4", url=ev["fileUrl"], qualityNote=f"File {ev['file']} published on Internet Archive item {ident}."))
        sources.append(dict(common, playbackType="embed", url=ev["embedUrl"], qualityNote="Internet Archive's own player for this item."))
        lic_words = {"public-domain-mark": "a Public Domain Mark", "public-domain": "a public-domain statement", "cc0": "CC0"}.get(lic_type, lic_type.upper())
        description = f"{r['blurb']} The Internet Archive item carries {lic_words}."
        note = r.get("note")
        if r.get("file"):
            note = (note + " " if note else "") + f"Plays one film, {r['file']}, from the multi-film item {ident}."
        review = pending_review(r["kids"], ev["checkedAt"]) if r.get("kids") else None
        rows.append(base_row(r["slug"], r["title"], description, r["year"], ev["runtimeSeconds"], r["genres"], r["language"], r["country"],
                             r["director"], r["cast"], r["type"], r["age"], f"https://archive.org/services/img/{ident}", r["cats"], note,
                             sources, review, ev["checkedAt"]))
        rows[-1]["archiveIdentifier"] = ident
    return rows


def yt_rows(evidence: dict) -> list[dict]:
    rows = []
    for r in additions.YT:
        ev = evidence.get(r["slug"] or "yt:" + r["vid"])
        if not ev or not ev.get("ok"):
            continue
        holder_name, channel, about, _site = additions.YT_HOLDERS[r["holder"]]
        title = r["title"] or episode_title(r["holder"], ev["sourceTitle"])
        slug = r["slug"] or slugify(title)
        year = r["year"] or int((ev.get("uploadDate") or "2000")[:4])
        channel_url = f"https://www.youtube.com/channel/{channel}"
        watch = f"https://www.youtube.com/watch?v={r['vid']}"
        lic_type, lic_url = "rights-holder-official-embed", channel_url
        if r["vid"] == "R6MlUcmOul8":  # Tears of Steel: the upload's own description states CC BY 3.0
            lic_type, lic_url = "cc-by-3.0", "https://creativecommons.org/licenses/by/3.0/"
        territories = ev["territories"]
        quality = "YouTube's own embedded player, loaded from youtube-nocookie.com, from the rights holder's official channel."
        if territories != ["WORLD"]:
            quality += f" The rights holder allows playback in {len(territories)} countries only."
        sources = [dict(
            providerSlug="youtube", playbackType="embed", url=ev["embedUrl"], licenceType=lic_type, licenceEvidenceUrl=lic_url,
            sourceRecordUrl=watch, licenceTerritories=territories, rightsVerified=True, playbackStatus="available",
            lastVerifiedAt=ev["checkedAt"], rightsHolder=holder_name, rightsHolderSource=r["holder"], subtitles=[], qualityNote=quality,
        )]
        if r.get("blurb") and r["blurb"] != "title":
            summary = r["blurb"]
        else:
            summary = strip_symbols(first_paragraph(ev.get("sourceDescription", "")))
            if len(summary) < 40 or JUNK.match(summary):
                summary = f"Full episode of {SERIES_NAMES.get(r['holder'], title)}, from the series' official channel."
        description = f"{summary} Played from {holder_name}'s official YouTube channel."
        note = (
            f"Uploaded by the rights holder's channel {channel_url} ({about}) on {(ev.get('uploadDate') or '')[:10]}. "
            "Embedding was confirmed with YouTube oEmbed and the watch page. YouTube and the rights holder control ads and availability."
        )
        if r.get("note"):
            note += " " + r["note"]
        review = pending_review(r["kids"], ev["checkedAt"]) if r.get("kids") else None
        rows.append(base_row(slug, title, description, year, ev["runtimeSeconds"], r["genres"], r["language"], r["country"], r["director"],
                             r["cast"], r["type"], r["age"], f"https://i.ytimg.com/vi/{r['vid']}/hqdefault.jpg", r["cats"], note, sources,
                             review, ev["checkedAt"]))
    return rows


def add_verified_additions(rows: list[dict], root: Path) -> None:
    path = root / "data" / "additions-evidence.json"
    if not path.exists():
        return
    evidence = json.loads(path.read_text(encoding="utf-8"))
    taken = {row["slug"] for row in rows}
    for row in ia_rows(evidence) + yt_rows(evidence):
        if row["slug"] in taken:
            raise SystemExit(f"duplicate slug {row['slug']}")
        taken.add(row["slug"])
        rows.append(row)
