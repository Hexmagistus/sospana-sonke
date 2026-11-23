"""Catalogue additions, checked 23 November 2026.

Every row here names one real upload. Nothing in this file is played until
`verify_additions.py` has confirmed it live and written the result to
`data/additions-evidence.json`. `build_catalog.py` drops any row without a
passing evidence record.

Two kinds of source are used:

* Internet Archive items whose own metadata carries a `licenseurl` for a
  public-domain mark, CC0, or a CC BY licence. The licence URL is read from the
  archive metadata API at verification time, not typed here.
* Full films and episodes uploaded to YouTube by the channel that made or owns
  them, played through YouTube's own embed. Embedding is checked with the
  oEmbed endpoint and the watch page's playability status. These are not
  open-licence titles. Permission to show them comes from the rights holder
  publishing them with embedding switched on, so the rights holder's channel
  is the evidence record.

Kids candidates are marked `kids=` with the age group a reviewer should check.
They get a *pending* review and are never placed in a Kids Cinema shelf until a
person approves them.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Rights holders behind the YouTube rows. `slug` becomes a content_sources row.
# ---------------------------------------------------------------------------
YT_HOLDERS = {
    "heartlines": ("Heartlines (HeartlinesZA)", "UCOaqwjRfP5JbInuqIobjaxQ", "South African non-profit that produced the Heartlines and Fathers Matter films.", "https://www.heartlines.org.za"),
    "shuga-global": ("MTV Shuga / MTV Staying Alive Foundation (Shuga Global)", "UCoJ0_TRpXzOfKJR3dllhTlg", "Official MTV Shuga channel run by the MTV Staying Alive Foundation.", "https://www.mtvshuga.com"),
    "triggerfish": ("Triggerfish Animation Studios", "UCSvKuNd_Qbt659Q9xGdHa0g", "Cape Town animation studio; official channel.", "https://www.triggerfish.com"),
    "amerley-productions": ("Amerley Productions (An African City)", "UCqAfv5ce1LfOCcbL5kPm-cA", "Producer of the series An African City; official channel.", "https://www.youtube.com/channel/UCqAfv5ce1LfOCcbL5kPm-cA"),
    "ubongo": ("Ubongo (Ubongo Kids English)", "UCjsrL7gPn-S5SJJcKp-OYUA", "Tanzanian non-profit edutainment studio; official channel.", "https://www.ubongo.org"),
    "akili-and-me": ("Ubongo (Akili and Me)", "UC0TLvo891eEEM6HGC5ON7ug", "Official Akili and Me channel run by Ubongo, Tanzania.", "https://www.ubongo.org"),
    "tinga-tinga": ("Tinga Tinga Tales Official", "UCWQLkOZV1aHXB0ihn2EwSbw", "Official channel of the Tinga Tinga Tales series.", "https://www.youtube.com/channel/UCWQLkOZV1aHXB0ihn2EwSbw"),
    "bino-and-fino": ("Bino and Fino", "UC9RRs4_NoXdOOHuhPHhwlHQ", "Official channel of the Nigerian children's series Bino and Fino.", "https://www.youtube.com/channel/UC9RRs4_NoXdOOHuhPHhwlHQ"),
    "supa-strikas": ("Supa Strikas", "UCdtojT_ZwTRlZThoBSMVhoQ", "Official channel of the South African-created Supa Strikas cartoon.", "https://www.youtube.com/channel/UCdtojT_ZwTRlZThoBSMVhoQ"),
    "kap-stream": ("Kunle Afolayan Productions (KAP STREAM)", "UCPdsCoSqO4dZcnkX_4do6hA", "Channel carrying Kunle Afolayan Productions' own films.", "https://www.youtube.com/channel/UCPdsCoSqO4dZcnkX_4do6hA"),
    "omoni-oboli": ("Omoni Oboli TV", "UCbvdwZvZgdl-pPyomEmaEfg", "Filmmaker Omoni Oboli's own channel for her productions.", "https://www.youtube.com/channel/UCbvdwZvZgdl-pPyomEmaEfg"),
    "wakaliwood": ("Ramon Film Productions (Official Wakaliwood)", "UCYK-lJOeYdoKuDDdGscCFMA", "Official channel of Nabwana IGG's Wakaliwood studio, Uganda.", "https://wakaliwood.com"),
    "netflix": ("Netflix", "UCWOA1ZGywLbqmigxE4Qlvuw", "Netflix's official channel. Our Planet was released there in full for free viewing.", "https://www.netflix.com"),
    "gundam-intl": ("Bandai Namco Filmworks (GUNDAM CHANNEL INTL)", "UCejtUitnpnf8Be-v5NuDSLw", "Official international Gundam channel. Region limits are set by the rights holder.", "https://www.youtube.com/channel/UCejtUitnpnf8Be-v5NuDSLw"),
    "crunchyroll": ("Crunchyroll (official channel)", "UC6pGDc4bFGD1_36IKv3FnYg", "Crunchyroll, the licensed anime distributor, posts free full episodes on its official channel. Region limits are set by Crunchyroll.", "https://www.youtube.com/channel/UC6pGDc4bFGD1_36IKv3FnYg"),
    "beyblade": ("BEYBLADE English - Official Channel", "UCktgoAFaL39_rYfiMZiD9jw", "The official English Beyblade channel posts full episodes. Region limits are set by the rights holder.", "https://www.youtube.com/channel/UCktgoAFaL39_rYfiMZiD9jw"),
    "yugioh": ("Official Yu-Gi-Oh! (Konami)", "UCZuVXrpKTUn_KEzRQgFgMWg", "The official Yu-Gi-Oh! channel posts full episodes. Region limits are set by the rights holder.", "https://www.youtube.com/channel/UCZuVXrpKTUn_KEzRQgFgMWg"),
    "pokemon": ("The Official Pokémon YouTube channel", "UCFctpiB_Hnlk3ejWfHqSm6Q", "The Pokémon Company International posts free full episodes on its official channel.", "https://www.youtube.com/channel/UCFctpiB_Hnlk3ejWfHqSm6Q"),
    "tezuka": ("Tezuka Productions (official channel)", "UCyach7GHJDlXTv6h3fcNwqg", "Tezuka Productions' official channel. Some episodes are posted for a limited period, so they are re-checked before each release.", "https://www.youtube.com/channel/UCyach7GHJDlXTv6h3fcNwqg"),
    "blender-studio": ("Blender Studio", "UCz75RVbH8q2jdBJ4SnwuZZQ", "Blender Foundation's film studio; official channel for its open movies.", "https://studio.blender.org"),
    "blender": ("Blender Foundation (Blender)", "UCSMOQeBJ2RAnuFungnQOxLg", "Official Blender channel.", "https://www.blender.org"),
}

ZA, TZ, KE, NG, GH, UG = "South Africa", "Tanzania", "Kenya", "Nigeria", "Ghana", "Uganda"

# vid, slug, title, year, runtime from evidence, genres, language, country, director, cast,
# type, age, categories, holder, kids (age group to review) or None, extra note
YT: list[dict] = []


def yt(vid, slug, title, year, genres, language, country, director, cast, ctype, age, cats, holder, kids=None, note=None, blurb=None):
    YT.append(dict(vid=vid, slug=slug, title=title, year=year, genres=genres, language=language, country=country,
                   director=director, cast=cast, type=ctype, age=age, cats=cats, holder=holder, kids=kids, note=note, blurb=blurb))


SA_FILM = ["south-african-movies", "african-cinema", "drama"]

# Heartlines (South Africa)
yt("AjrFuIetIQE", "nothing-for-mahala", "Nothing for Mahala", 2013, ["Comedy", "Drama"], "English", ZA, "Rolie Nikiwe", ["Thapelo Mokoena"], "movie", "13+", ["south-african-movies", "african-cinema", "comedy", "drama"], "heartlines")
yt("3yQW0YYhtg0", "hopeville", "Hopeville", 2009, ["Drama"], "English", ZA, "John Trengove", [], "movie", "13+", SA_FILM, "heartlines")
yt("VRqizoxWYR4", "playing-dad", "Playing Dad", 2025, ["Drama", "Family"], "English", ZA, "See the source record", ["Vincent Mahlape"], "movie", "All", SA_FILM + ["short-films"], "heartlines")
yt("uQEpzoYQVPQ", "in-time-fathers-matter", "In Time (Fathers Matter)", 2022, ["Drama"], "English", ZA, "See the source record", [], "short", "13+", SA_FILM + ["short-films"], "heartlines")
yt("2g6Kbe2Z2jc", "everything-a-boy-could-want", "Everything a Boy Could Want (Fathers Matter)", 2022, ["Drama"], "English", ZA, "See the source record", [], "short", "13+", SA_FILM + ["short-films"], "heartlines")
yt("m-I1vUkFw50", "melodi-fathers-matter", "Melodi (Fathers Matter)", 2022, ["Drama"], "English", ZA, "See the source record", [], "short", "13+", SA_FILM + ["short-films"], "heartlines")
yt("XSiQoJL1XM4", "airwalker-fathers-matter", "Airwalker (Fathers Matter)", 2022, ["Drama"], "English", ZA, "See the source record", [], "short", "13+", SA_FILM + ["short-films"], "heartlines")
yt("IuMiThlBebI", "manskap-fathers-matter", "Manskap (Fathers Matter)", 2022, ["Drama"], "English and Afrikaans", ZA, "See the source record", [], "short", "13+", SA_FILM + ["short-films"], "heartlines")
yt("qwC9G8QHVRE", "family-portrait-fathers-matter", "Family Portrait (Fathers Matter)", 2022, ["Drama"], "English", ZA, "See the source record", [], "short", "13+", SA_FILM + ["short-films"], "heartlines")

# Triggerfish (South Africa)
yt("ls5J7caQj7A", "belly-flop", "Belly Flop", 2018, ["Animation", "Short", "Family"], "No dialogue", ZA, "See the source record", [], "short", "All", ["south-african-movies", "african-cinema", "animated-movies", "short-films"], "triggerfish", kids="6-8")
yt("kn2dxYYYoKw", "troll-girl", "Troll Girl", 2026, ["Animation", "Short", "Fantasy"], "English", ZA, "Kay Carmichael", [], "short", "9+", ["south-african-movies", "african-cinema", "animated-movies", "short-films"], "triggerfish", kids="9-12")
yt("Tzn1cAnst8c", "also-for-grownups", "Also For Grownups: Emerging Voices in South African Animation", 2024, ["Documentary"], "English", ZA, "Tim Wege, Pete O'Donoghue", [], "documentary", "All", ["south-african-movies", "african-cinema", "documentaries", "educational-movies"], "triggerfish")

# MTV Shuga: Down South (South Africa)
SHUGA_SA = ["south-african-movies", "african-cinema", "tv-series", "drama"]
for vid, s, e, name, yr in [
    ("MteEZk0__n8", 1, 1, "Welcome Home", 2017), ("nXk6GUXBq0E", 1, 2, "Sex Pest", 2017), ("pjk63JNyFO0", 1, 4, "Love Hurts", 2017),
    ("YPUqeIw8xQk", 1, 5, "Daddy's Home", 2017), ("7uQy_tyGxmY", 1, 6, "Choices", 2017), ("h577_Xkh5fk", 1, 8, "Head in the Sand", 2017),
    ("HpuL_4Hf4nw", 2, 1, None, 2019), ("uUpNMP_O-aA", 2, 2, None, 2019), ("Xx9hvGN5v2w", 2, 3, None, 2019), ("Cn4jMvH18RQ", 2, 4, None, 2019),
    ("KsNtgs3Sv9c", 2, 5, None, 2019), ("gxilPEjilxI", 2, 6, None, 2019), ("sZud3XkRak8", 2, 7, None, 2019), ("6M56SYkSz-w", 2, 8, None, 2019),
    ("KGaocqugUPg", 2, 9, None, 2019), ("DcghZLwsGnQ", 2, 10, None, 2019),
    ("aNWbJ99I7es", 3, 1, None, 2023), ("l-7TnYigx-c", 3, 2, None, 2023), ("W5-Td8UcWBw", 3, 3, None, 2023), ("1758rwDNl78", 3, 4, None, 2023),
    ("7-c5oZ3oaRc", 3, 5, None, 2023), ("6IwNP1fPZFA", 3, 6, None, 2023), ("Kjx991G_xgA", 3, 7, None, 2023), ("bPjoHiFJCak", 3, 8, None, 2023),
    ("pAh3dfFUhJg", 3, 10, None, 2023),
]:
    t = f"MTV Shuga: Down South S{s} E{e}" + (f": {name}" if name else "")
    yt(vid, f"mtv-shuga-down-south-s{s}-e{e}", t, yr, ["Drama", "Series"], "English and South African languages", ZA, "See the source record", [], "series", "16+", SHUGA_SA, "shuga-global",
       blurb=f"Season {s}, episode {e} of MTV Shuga: Down South, the MTV Staying Alive Foundation's South African drama about young people, relationships, sexual health and HIV.")

# MTV Shuga Mashariki (Kenya) and Shuga Naija (Nigeria)
for vid, e in [("suapN_w1BA0", 1), ("CwDUPnNdc4s", 2), ("GpLswPjSaSs", 3), ("sapM71z2XVE", 6), ("TjonID1wkuk", 8)]:
    yt(vid, f"mtv-shuga-mashariki-s1-e{e}", f"MTV Shuga Mashariki S1 E{e}", 2025, ["Drama", "Series"], "English and Swahili", KE, "See the source record", [], "series", "16+", ["african-cinema", "tv-series", "drama"], "shuga-global",
       blurb=f"Season 1, episode {e} of MTV Shuga Mashariki, the East African MTV Shuga drama about students, relationships and sexual health.")
for vid, s, e, name, yr in [("Jo4l1VJUFkQ", 1, 1, "Home Coming", 2013), ("wxH7kqyYJvU", 3, 1, None, 2018), ("18w6BVGQebU", 3, 5, None, 2018), ("hUGurROEaqg", 3, 8, None, 2018), ("OXk45pOWo_I", 3, 10, None, 2018)]:
    t = f"MTV Shuga Naija S{s} E{e}" + (f": {name}" if name else "")
    yt(vid, f"mtv-shuga-naija-s{s}-e{e}", t, yr, ["Drama", "Series"], "English", NG, "See the source record", [], "series", "16+", ["african-cinema", "tv-series", "drama"], "shuga-global",
       blurb=f"Season {s}, episode {e} of MTV Shuga Naija, the MTV Staying Alive Foundation's Nigerian drama about young people, relationships and sexual health.")

# An African City (Ghana), season 1. Episode 3 is age-restricted on YouTube, so it cannot be embedded and is left out.
for vid, e, name in [("kg7hUuWKe2U", 1, "The Return"), ("MtKX9qYPCuI", 2, "Sexual Real Estate"), ("ggCvrcVCUTI", 4, "A Customs Emergency"),
                     ("aw2RtHSeOa0", 5, "The Belly Button Test"), ("3yKSTT-VhVM", 6, "He Facebooked Me"), ("c0oGYhmMYSA", 7, "Condom Etiquette"),
                     ("o700gABAI2w", 8, "An Ode to Saturdays"), ("Moxu3EEHbvA", 9, "#TeamSade, #TeamNgozi"), ("MGq3UZksx3s", 10, "A Big Decision")]:
    yt(vid, f"an-african-city-s1-e{e}", f"An African City S1 E{e}: {name}", 2014, ["Comedy", "Drama", "Series"], "English", GH, "Nicole Amarteifio", [], "series", "16+", ["african-cinema", "tv-series", "comedy", "drama"], "amerley-productions",
       blurb=f"Episode {e} of the first season of An African City, Nicole Amarteifio's series about five women who have moved back home to Accra.")

# Nigeria and Uganda features from the producers' own channels
for vid, slug, title, year, genres, age, cats in [
    ("lU1Y7Lc4Pwo", "october-1", "October 1", 2014, ["Thriller", "Drama"], "16+", ["african-cinema", "mystery-and-thriller", "drama"]),
    ("ovI2x9AhQyQ", "figurine", "Figurine", 2009, ["Thriller", "Drama"], "13+", ["african-cinema", "mystery-and-thriller", "drama"]),
    ("E6d4OZ3lTRE", "phone-swap", "Phone Swap", 2012, ["Comedy", "Romance"], "13+", ["african-cinema", "comedy"]),
    ("douRZoRGv-o", "the-ceo", "The CEO", 2016, ["Thriller", "Drama"], "13+", ["african-cinema", "mystery-and-thriller", "drama"]),
]:
    yt(vid, slug, title, year, genres, "English", NG, "Kunle Afolayan", [], "movie", age, cats, "kap-stream")
for vid, slug, title, year in [("VooG7LMBMak", "a-bride-for-the-season", "A Bride for the Season", 2025),
                               ("7CQXWZ76YUQ", "married-for-the-weekend", "Married for the Weekend", 2026),
                               ("RHXre4lxzSI", "good-enough-omoni-oboli", "Good Enough", 2026)]:
    yt(vid, slug, title, year, ["Romance", "Drama"], "English", NG, "See the source record", [], "movie", "13+", ["african-cinema", "drama"], "omoni-oboli")
yt("KEoGrbKAyKE", "who-killed-captain-alex", "Who Killed Captain Alex?", 2010, ["Action", "Comedy"], "Luganda with English subtitles", UG, "Nabwana IGG", [], "movie", "16+", ["african-cinema", "action-and-adventure", "comedy", "independent-films"], "wakaliwood")

# Kids candidates from African studios (pending review)
for vid in ["o5NTEEpa8og", "xP5-UDRnPPk", "y3lBdDbXQjM", "kdQHTxSepNI", "rguC5BX1U68", "Zg6y4TrN7iQ", "EeLgIGT5vsE", "ekRhUHE7zZc"]:
    yt(vid, None, None, None, ["Animation", "Educational", "Series"], "English", TZ, "See the source record", [], "series", "All", ["african-cinema", "animated-movies", "educational-movies", "tv-series"], "ubongo", kids="6-8", blurb="title")
for vid in ["UEAh-UMV8nc", "abEw56x8B8U", "lWgOKtx81PQ", "CSmYYzcSRsU", "oZEU9994Y68"]:
    yt(vid, None, None, None, ["Animation", "Educational", "Series"], "English", TZ, "See the source record", [], "series", "All", ["african-cinema", "animated-movies", "educational-movies", "tv-series"], "akili-and-me", kids="preschool", blurb="title")
for vid in ["uT0sFhj38rY", "buaVue7ysTg", "wp-Y2f3FtGs", "q4FrMobz9Ak", "sTFQ5WndyDs"]:
    yt(vid, None, None, None, ["Animation", "Folk tale", "Series"], "English", KE, "See the source record", [], "series", "All", ["african-cinema", "animated-movies", "tv-series"], "tinga-tinga", kids="preschool", blurb="title")
for vid in ["FrjltcMXEVs", "d06uJgqgQ4M", "3PcWys9sVs0", "7O48Jh5ZCWo", "_BqBHj7hwOI", "Ez-1Uat-blM"]:
    yt(vid, None, None, None, ["Animation", "Educational", "Series"], "English", NG, "See the source record", [], "series", "All", ["african-cinema", "animated-movies", "educational-movies", "tv-series"], "bino-and-fino", kids="preschool", blurb="title")
for vid in ["Nu0DnhveFRY", "cyZBvhEjJIs", "lxRPmMl-RYY"]:
    yt(vid, None, None, None, ["Animation", "Sport", "Series"], "English", ZA, "See the source record", [], "series", "All", ["south-african-movies", "african-cinema", "animated-movies", "tv-series", "action-and-adventure"], "supa-strikas", kids="6-8", blurb="title")

# Nature: Our Planet (Netflix's free full-episode release)
OUR_PLANET = [("GfO-3Oir-qM", "One Planet"), ("um2Q9aUecy0", "Jungles"), ("r9PeYPHdpNo", "Coastal Seas"), ("XmtXC_n6X6Q", "From Deserts to Grasslands"),
              ("9FqwhW0B3tY", "High Seas"), ("R2DU85qLfJQ", "Fresh Water"), ("JkaxUblCGz0", "Forests"), ("cTQ3Ko9ZKg8", "Frozen Worlds")]
for vid, name in OUR_PLANET:
    slug = "our-planet-" + name.lower().replace(" ", "-")
    yt(vid, slug, f"Our Planet: {name}", 2019, ["Documentary", "Nature"], "English", "United Kingdom", "Alastair Fothergill (series producer)", ["David Attenborough (narrator)"], "documentary", "All",
       ["documentaries", "nature-and-wildlife", "international-movies", "educational-movies", "tv-series"], "netflix", kids="family",
       blurb=f"The {name} episode of Our Planet (2019), the nature series narrated by David Attenborough. Netflix released the full episodes on YouTube for free viewing.")

# Anime: official Gundam uploads (region-limited by the rights holder)
for vid, slug, title, year, ctype, blurb in [
    ("YYqJMKhaLhk", "mobile-suit-gundam-i", "Mobile Suit Gundam I (film)", 1981, "movie", "The first of the three films edited from the 1979 Mobile Suit Gundam television series."),
    ("B60vNz15Hzg", "mobile-suit-gundam-ii-soldiers-of-sorrow", "Mobile Suit Gundam II: Soldiers of Sorrow", 1981, "movie", "The second of the three films edited from the 1979 Mobile Suit Gundam television series."),
    ("mAxCyrDuNiA", "mobile-suit-gundam-chars-counterattack", "Mobile Suit Gundam: Char's Counterattack", 1988, "movie", "Yoshiyuki Tomino's 1988 feature about the last clash between Amuro Ray and Char Aznable."),
    ("7jLv_j-m8F4", "mobile-suit-gundam-00-s1-e1", "Mobile Suit Gundam 00 S1 E1: Celestial Being", 2007, "series", "The first episode of Mobile Suit Gundam 00 (2007)."),
    ("4AbgG1rVFrk", "mobile-suit-gundam-seed-destiny-e1", "Mobile Suit Gundam SEED DESTINY E1 (English dub)", 2004, "series", "The first episode of Mobile Suit Gundam SEED Destiny (2004), in the English dub."),
]:
    cats = ["anime", "animated-movies", "international-movies", "action-and-adventure"] + (["tv-series"] if ctype == "series" else [])
    yt(vid, slug, title, year, ["Anime", "Science Fiction", "Action"], "Japanese with subtitles" if "dub" not in title else "English", "Japan",
       "Yoshiyuki Tomino" if year < 2000 else "See the source record", [], ctype, "13+", cats, "gundam-intl", blurb=blurb)

# Anime shelf (added 23 November 2026). Full episodes and films posted by the
# rights holder or licensed distributor on its own official channel, with
# embedding on and South Africa inside the allowed regions. Children's titles
# are recorded as pending kids review. Skipped after checking: RetroCrush
# uploads (US and Canada only), Astro Boy 1980 on RetroCrush (embedding off),
# JUJUTSU KAISEN and The Quintessential Quintuplets on Crunchyroll (not
# available in South Africa), Tezuka Productions' Japanese-only uploads with no
# English captions, Muse Asia and Ani-One Asia (Asia-only uploads).
JSUB = "Japanese with English subtitles"
SUBDUB = "Japanese with English subtitles (English dub also on the official channel)"
ANIME_TV = ["anime", "animated-movies", "international-movies", "tv-series"]
for vid, slug, title, year, lang, genres, extra, age, kids, blurb in [
    ("Jx5GcsjMOSs", "mobile-suit-gundam-e1", "Mobile Suit Gundam E1: Gundam Rises", 1979, JSUB, ["Anime", "Science Fiction", "Action"], ["action-and-adventure", "classic-cinema"], "13+", None, "The first episode of the 1979 series that started the Gundam franchise, directed by Yoshiyuki Tomino."),
    ("8KCS-QIEg2U", "mobile-suit-gundam-the-origin-e1", "Mobile Suit Gundam: The Origin E1", 2019, JSUB, ["Anime", "Science Fiction", "Action"], ["action-and-adventure"], "13+", None, "The first episode of The Origin, Yoshikazu Yasuhiko's retelling of Char Aznable's early life."),
    ("9isbRbLD2GE", "mobile-suit-gundam-unicorn-re0096-e1", "Mobile Suit Gundam Unicorn RE:0096 E1", 2016, JSUB, ["Anime", "Science Fiction", "Action"], ["action-and-adventure"], "13+", None, "The first episode of the television version of Gundam Unicorn."),
    ("2B_njMCRCvU", "gundam-the-witch-from-mercury-e1", "Mobile Suit Gundam the Witch from Mercury E1", 2022, JSUB, ["Anime", "Science Fiction", "Drama"], ["action-and-adventure", "drama"], "13+", None, "The first episode of The Witch from Mercury, set at a school for mobile-suit pilots."),
    ("U10iG69axKc", "mobile-suit-gundam-seed-hd-e1", "Mobile Suit Gundam SEED (HD Remaster) E1", 2002, JSUB, ["Anime", "Science Fiction", "Action"], ["action-and-adventure"], "13+", None, "The first episode of Gundam SEED, in the HD remaster."),
    ("ZzckBkxy0BM", "mobile-suit-gundam-seed-e1-english-dub", "Mobile Suit Gundam SEED E1 (English dub)", 2002, "English", ["Anime", "Science Fiction", "Action"], ["action-and-adventure"], "13+", None, "The first episode of Gundam SEED, in the English dub."),
    ("TTnmp3_vAX4", "after-war-gundam-x-e1", "After War Gundam X E1", 1996, JSUB, ["Anime", "Science Fiction", "Action"], ["action-and-adventure"], "13+", None, "The first episode of After War Gundam X, set fifteen years after a war that wrecked the Earth."),
    ("eKFM63BIxzY", "mobile-fighter-g-gundam-e1", "Mobile Fighter G Gundam E1", 1994, JSUB, ["Anime", "Action", "Martial arts"], ["action-and-adventure"], "13+", None, "The first episode of G Gundam, where nations settle disputes with a Gundam fighting tournament."),
    ("bktN_TdP6yI", "gundam-build-divers-e1", "Gundam Build Divers E1: Welcome to GBN", 2018, JSUB, ["Anime", "Action", "Comedy"], ["action-and-adventure", "comedy"], "9+", "9-12", "The first episode of Gundam Build Divers, about friends who battle with model kits in an online world."),
    ("a_ai9Ekrg58", "sd-gundam-world-heroes-e1", "SD Gundam World Heroes E1: Falling Destiny", 2021, JSUB, ["Anime", "Action", "Comedy"], ["action-and-adventure", "comedy"], "9+", "9-12", "The first episode of SD Gundam World Heroes, a comic action series with super-deformed Gundams."),
    ("TEp52IJvERA", "gundam-reconguista-in-g-e1", "Gundam Reconguista in G E1", 2014, JSUB, ["Anime", "Science Fiction", "Action"], ["action-and-adventure"], "13+", None, "The first episode of Reconguista in G, Yoshiyuki Tomino's 2014 Gundam series."),
    ("JJMV4WrybjM", "mobile-suit-gundam-iii-encounters-in-space", "Mobile Suit Gundam III: Encounters in Space", 1982, JSUB, ["Anime", "Science Fiction", "Action"], ["action-and-adventure", "classic-cinema"], "13+", None, "The third of the three films edited from the 1979 Mobile Suit Gundam series."),
]:
    ctype = "movie" if "iii" in slug else "series"
    cats = ["anime", "animated-movies", "international-movies"] + (["tv-series"] if ctype == "series" else []) + extra
    yt(vid, slug, title, year, genres, lang, "Japan", "Yoshiyuki Tomino" if slug.startswith(("mobile-suit-gundam-e1", "mobile-suit-gundam-iii", "gundam-reconguista")) else "See the source record", [], ctype, age, cats, "gundam-intl", kids=kids, blurb=blurb)

for vid, slug, title, year, country, genres, extra, age, kids in [
    ("JxpVIn26nfk", "black-clover-e1", "Black Clover E1: Asta and Yuno", 2017, "Japan", ["Anime", "Fantasy", "Action"], ["action-and-adventure"], "13+", None),
    ("EHRmWyzIpSw", "the-apothecary-diaries-e1", "The Apothecary Diaries E1: Maomao", 2023, "Japan", ["Anime", "Mystery", "Drama"], ["mystery-and-thriller", "drama"], "13+", None),
    ("zL3ZY2cTsl0", "magic-knight-rayearth-e1", "Magic Knight Rayearth E1: From Another World", 1994, "Japan", ["Anime", "Fantasy", "Adventure"], ["action-and-adventure"], "9+", "9-12"),
    ("Lzncql2NAYY", "magic-knight-rayearth-e2", "Magic Knight Rayearth E2: The Legend Begins", 1994, "Japan", ["Anime", "Fantasy", "Adventure"], ["action-and-adventure"], "9+", "9-12"),
    ("73k_5FNpWvU", "magic-knight-rayearth-e3", "Magic Knight Rayearth E3: All in the Same Boat", 1994, "Japan", ["Anime", "Fantasy", "Adventure"], ["action-and-adventure"], "9+", "9-12"),
    ("QxRCVPqN7lw", "witch-hat-atelier-e1", "Witch Hat Atelier E1: The Magic That Started Everything", None, "Japan", ["Anime", "Fantasy"], ["action-and-adventure"], "9+", "9-12"),
    ("D261aPLKOuk", "gachiakuta-e1", "Gachiakuta E1: The Sphere", 2025, "Japan", ["Anime", "Action", "Fantasy"], ["action-and-adventure"], "16+", None),
    ("UGnH_Yzmemw", "the-beginning-after-the-end-e1", "The Beginning After The End E1: The Rebirth of the King", 2025, "Japan", ["Anime", "Fantasy", "Action"], ["action-and-adventure"], "13+", None),
    ("GYezZx5dVVc", "kaiju-girl-caramelise-e1", "Kaiju Girl Caramelise E1: The Kaiju Girl Appears in Tokyo", None, "Japan", ["Anime", "Romance", "Comedy"], ["comedy"], "13+", None),
    ("Vb7OUP9bxfM", "goodbye-lara-e1", "Goodbye, Lara E1: Mermaid Princess Lara", None, "Japan", ["Anime", "Fantasy", "Drama"], ["drama"], "13+", None),
    ("5LM0iTQrnP4", "overgeared-e1", "Overgeared E1: Legendary Class", None, "South Korea", ["Anime", "Fantasy", "Action"], ["action-and-adventure"], "13+", None),
    ("9zK-on2SSd8", "psyren-e1", "PSYREN E1: Urban Legend", None, "Japan", ["Anime", "Science Fiction", "Thriller"], ["mystery-and-thriller", "action-and-adventure"], "16+", None),
    ("eff15vYzN0o", "to-be-hero-x-e1", "TO BE HERO X E1: NICE", 2025, "China", ["Anime", "Action", "Superhero"], ["action-and-adventure"], "13+", None),
    ("PZIy0Ct6KLo", "umamusume-pretty-derby-e1", "Umamusume: Pretty Derby E1: Gate of Dreams!", 2018, "Japan", ["Anime", "Sport", "Comedy"], ["comedy"], "9+", None),
]:
    series = title.split(" E")[0]
    yt(vid, slug, title, year, genres, JSUB if slug in {"the-apothecary-diaries-e1", "umamusume-pretty-derby-e1"} else SUBDUB, country, "See the source record", [], "series", age, ANIME_TV + extra, "crunchyroll", kids=kids,
       blurb=f"A free full episode of {series}, posted by Crunchyroll, the series' licensed distributor, on its official channel.")

for vid, slug, title, year, holder, age, kids, blurb in [
    ("q8l9UGsmvWs", "beyblade-metal-fusion-e1", "Beyblade: Metal Fusion E1: Pegasus Has Landed!", 2009, "beyblade", "9+", "9-12", "The first episode of Beyblade: Metal Fusion, in English, from the official Beyblade channel."),
    ("dH0rb40Cca4", "beyblade-metal-masters-e1", "Beyblade: Metal Masters E1: Seeking the Legend", 2010, "beyblade", "9+", "9-12", "The first episode of Beyblade: Metal Masters, in English, from the official Beyblade channel."),
    ("v9ok0BuXnZc", "beyblade-x-e1", "Beyblade X E1: X", 2023, "beyblade", "9+", "9-12", "The first episode of Beyblade X, in English, from the official Beyblade channel."),
    ("x7jBM_7e4bo", "beyblade-burst-evolution-e1-e2", "Beyblade Burst Evolution E1 and E2", 2017, "beyblade", "9+", "9-12", "The first two episodes of Beyblade Burst Evolution, in English, from the official Beyblade channel."),
    ("DdCSFeG7Ajg", "beyblade-v-force-e1-e2", "Beyblade V-Force E1 and E2", 2002, "beyblade", "9+", "9-12", "The first two episodes of Beyblade V-Force, in English, from the official Beyblade channel."),
    ("2ot9eV9DybI", "yu-gi-oh-duel-monsters-s1-e1", "Yu-Gi-Oh! Duel Monsters S1 E1: The Heart of the Cards", 2000, "yugioh", "9+", "9-12", "The first episode of Yu-Gi-Oh! Duel Monsters, in English, from the official Yu-Gi-Oh! channel."),
    ("XWpOWw0rU3w", "yu-gi-oh-sevens-s1-e1", "Yu-Gi-Oh! SEVENS S1 E1: Ready for the Rush!", 2020, "yugioh", "9+", "9-12", "The first episode of Yu-Gi-Oh! SEVENS, in English, from the official Yu-Gi-Oh! channel."),
    ("1Z7saW4wwSk", "pokemon-horizons-s1-e1-e2", "Pokémon Horizons S1 E1 and E2: The Pendant That Starts It All", 2023, "pokemon", "All", "6-8", "The first two episodes of Pokémon Horizons: The Series, in English, from the official Pokémon channel."),
    ("VmTSAWTQhmE", "pokemon-horizons-s2-e1", "Pokémon Horizons S2 E1: Welcome to Naranja Academy!", None, "pokemon", "All", "6-8", "The first episode of season 2 of Pokémon Horizons: The Series, in English, from the official Pokémon channel."),
    ("iE-at9RW3VI", "pokemon-horizons-s3-e1", "Pokémon Horizons S3 E1: Eyes to the Skies Once Again (Part 1)", None, "pokemon", "All", "6-8", "The first episode of season 3 of Pokémon Horizons: The Series, in English, from the official Pokémon channel."),
    ("17QAt19ivBs", "jungle-emperor-go-forward-leo-e1", "Jungle Emperor: Go Forward, Leo! E1: The White King", 1966, "tezuka", "All", "6-8", "The first episode of Jungle Emperor: Go Forward, Leo!, the 1966 sequel to Kimba the White Lion, from Tezuka Productions' official channel. Japanese audio with English captions. Tezuka Productions posts some episodes for a limited period."),
]:
    lang = "Japanese with English captions" if holder == "tezuka" else "English"
    genres = ["Anime", "Adventure", "Family"] if holder in {"pokemon", "tezuka"} else ["Anime", "Action", "Sport"]
    extra = ["action-and-adventure"]
    yt(vid, slug, title, year, genres, lang, "Japan", "Osamu Tezuka (original work)" if holder == "tezuka" else "See the source record", [], "series", age, ANIME_TV + extra, holder, kids=kids, blurb=blurb)


# Blender open movies (official uploads)
BLENDER_BLURBS = {'tears-of-steel': "Blender Foundation's 2012 live-action and visual-effects short, about a group of warriors and scientists in a future Amsterdam. Released under CC BY 3.0.", 'spring-blender': "Blender Studio's 2019 short about a shepherd girl and her dog who face ancient spirits to keep the cycle of life going.", 'sprite-fright': "Blender Studio's 2021 horror-comedy short about teenagers who meet the wrong forest sprites.", 'charge-blender': "Blender Studio's 2022 action short, made entirely in Blender.", 'wing-it': "Blender Studio's 2023 comedy short about a cat and a dog who build a rocket.", 'agent-327-operation-barbershop': "Blender Animation Studio's 2017 teaser for a feature based on Martin Lodewijk's Dutch comic series Agent 327.", 'coffee-run': "Blender Studio's 2020 short about a young woman running through memories of a past relationship.", 'caminandes-llamigos': 'The third Caminandes short (2016): in a Patagonian winter, Koro the llama meets a penguin.', 'hero-blender': "Blender's 2018 Grease Pencil showcase short, a 2D action piece made inside a 3D pipeline."}
for vid, slug, title, year, holder, director, age, kids in [
    ("R6MlUcmOul8", "tears-of-steel", "Tears of Steel", 2012, "blender", "Ian Hubert", "13+", None),
    ("WhWc3b3KhnY", "spring-blender", "Spring", 2019, "blender-studio", "Andy Goralczyk", "9+", "9-12"),
    ("_cMxraX_5RE", "sprite-fright", "Sprite Fright", 2021, "blender-studio", "Matthew Luhn, Hjalti Hjálmarsson", "13+", None),
    ("UXqq0ZvbOnk", "charge-blender", "Charge", 2022, "blender-studio", "Hjalti Hjálmarsson", "13+", None),
    ("u9lj-c29dxI", "wing-it", "Wing It!", 2023, "blender-studio", "Rik Schutte", "All", "6-8"),
    ("mN0zPOpADL4", "agent-327-operation-barbershop", "Agent 327: Operation Barbershop", 2017, "blender-studio", "Colin Levy, Hjalti Hjálmarsson", "13+", None),
    ("PVGeM40dABA", "coffee-run", "Coffee Run", 2020, "blender-studio", "Hjalti Hjálmarsson", "All", None),
    ("SkVqJ1SGeL0", "caminandes-llamigos", "Caminandes 3: Llamigos", 2016, "blender", "Pablo Vazquez", "All", "preschool"),
    ("pKmSdY56VtY", "hero-blender", "Hero", 2018, "blender", "Daniel M. Lara", "9+", None),
]:
    yt(vid, slug, title, year, ["Animation", "Short"], "English" if slug in {"tears-of-steel", "sprite-fright"} else "No dialogue", "Netherlands", director, [], "short", age,
       ["international-movies", "animated-movies", "short-films", "independent-films"], holder, kids=kids, blurb=BLENDER_BLURBS[slug])


# ---------------------------------------------------------------------------
# Internet Archive rows. `file` picks one video inside a multi-film item.
# ---------------------------------------------------------------------------
IA: list[dict] = []


def ia(identifier, slug, title, year, genres, language, country, director, cast, ctype, age, cats, blurb, file=None, kids=None, note=None):
    IA.append(dict(identifier=identifier, slug=slug, title=title, year=year, genres=genres, language=language, country=country, director=director,
                   cast=cast, type=ctype, age=age, cats=cats, blurb=blurb, file=file, kids=kids, note=note))


US = "United States"
CLASSIC = ["international-movies", "classic-cinema"]

# Chaplin shorts
for ident, slug, title, year in [
    ("CC_1914_02_07_KidsAutoRaceAtVenice", "kid-auto-races-at-venice", "Kid Auto Races at Venice", 1914),
    ("CC_1915_12_18_ABurlesqueOnCarmen", "a-burlesque-on-carmen", "A Burlesque on Carmen", 1915),
    ("CC_1916_05_15_TheFloorwalker", "the-floorwalker", "The Floorwalker", 1916),
    ("CC_1916_09_04_TheCount", "the-count-chaplin", "The Count", 1916),
    ("CC_1916_10_02_ThePawnshop", "the-pawnshop", "The Pawnshop", 1916),
    ("CC_1916_12_04_TheRink", "the-rink", "The Rink", 1916),
    ("CC_1917_04_16_TheCure", "the-cure", "The Cure", 1917),
]:
    ia(ident, slug, title, year, ["Comedy", "Silent", "Short"], "Silent", US, "Henry Lehrman" if year == 1914 else "Charlie Chaplin", ["Charlie Chaplin"], "short", "All",
       CLASSIC + ["comedy", "short-films"], f"Charlie Chaplin silent comedy short from {year}.")
ia("CC_1914_11_14_TilliesPuncturedRomance", "tillies-punctured-romance", "Tillie's Punctured Romance", 1914, ["Comedy", "Silent"], "Silent", US, "Mack Sennett",
   ["Marie Dressler", "Charlie Chaplin", "Mabel Normand"], "movie", "All", CLASSIC + ["comedy"], "Mack Sennett's 1914 feature comedy with Marie Dressler, Charlie Chaplin and Mabel Normand.")

# Features
F = [
    ("JungleBook", "jungle-book-1942", "Jungle Book", 1942, ["Adventure", "Family"], "English", US, "Zoltan Korda", ["Sabu"], "9+", ["action-and-adventure", "family-entertainment"], "Zoltan Korda's 1942 Technicolor adaptation of Rudyard Kipling's stories, with Sabu as Mowgli.", "family"),
    ("Sita_Sings_the_Blues", "sita-sings-the-blues", "Sita Sings the Blues", 2008, ["Animation", "Musical"], "English", US, "Nina Paley", [], "13+", ["animated-movies", "independent-films"], "Nina Paley's animated retelling of the Ramayana, set to 1920s jazz recordings and released by the filmmaker under CC0.", None),
    ("The_Pied_Piper_of_Hamelin", "the-pied-piper-of-hamelin-1957", "The Pied Piper of Hamelin", 1957, ["Musical", "Family", "Fantasy"], "English", US, "Bretaigne Windust", ["Van Johnson", "Claude Rains"], "All", ["family-entertainment"], "A 1957 musical version of the Pied Piper legend with Van Johnson and Claude Rains.", "family"),
    ("abraham_lincoln", "abraham-lincoln-1930", "Abraham Lincoln", 1930, ["Drama", "History"], "English", US, "D. W. Griffith", ["Walter Huston"], "13+", ["drama"], "D. W. Griffith's 1930 biography of Abraham Lincoln, with Walter Huston.", None),
    ("dressed_to_kill", "dressed-to-kill-1946", "Dressed to Kill", 1946, ["Mystery"], "English", US, "Roy William Neill", ["Basil Rathbone", "Nigel Bruce"], "13+", ["mystery-and-thriller"], "Basil Rathbone and Nigel Bruce as Holmes and Watson, tracking music boxes that hide a secret.", None),
    ("secret_weapon", "sherlock-holmes-and-the-secret-weapon", "Sherlock Holmes and the Secret Weapon", 1943, ["Mystery"], "English", US, "Roy William Neill", ["Basil Rathbone", "Nigel Bruce"], "13+", ["mystery-and-thriller"], "Holmes protects a scientist and his bombsight from Professor Moriarty during the Second World War.", None),
    ("TheFlyingDeuces", "the-flying-deuces", "The Flying Deuces", 1939, ["Comedy"], "English", US, "A. Edward Sutherland", ["Stan Laurel", "Oliver Hardy"], "All", ["comedy"], "Laurel and Hardy join the French Foreign Legion.", None),
    ("meet_john_doe", "meet-john-doe", "Meet John Doe", 1941, ["Drama", "Comedy"], "English", US, "Frank Capra", ["Gary Cooper", "Barbara Stanwyck"], "All", ["drama"], "Frank Capra's 1941 drama about a reporter's invented everyman, with Gary Cooper and Barbara Stanwyck.", None),
    ("little_princess", "the-little-princess-1939", "The Little Princess", 1939, ["Drama", "Family"], "English", US, "Walter Lang", ["Shirley Temple"], "All", ["family-entertainment", "drama"], "Shirley Temple in the 1939 Technicolor adaptation of Frances Hodgson Burnett's novel.", "family"),
    ("royal_wedding", "royal-wedding", "Royal Wedding", 1951, ["Musical", "Comedy"], "English", US, "Stanley Donen", ["Fred Astaire", "Jane Powell"], "All", ["comedy"], "Stanley Donen's 1951 musical with Fred Astaire and Jane Powell.", None),
    ("my_favorite_brunette", "my-favorite-brunette", "My Favorite Brunette", 1947, ["Comedy", "Mystery"], "English", US, "Elliott Nugent", ["Bob Hope", "Dorothy Lamour"], "All", ["comedy", "mystery-and-thriller"], "Bob Hope plays a baby photographer mistaken for a private detective.", None),
    ("mclintok_widescreen", "mclintock", "McLintock!", 1963, ["Western", "Comedy"], "English", US, "Andrew V. McLaglen", ["John Wayne", "Maureen O'Hara"], "13+", ["comedy", "action-and-adventure"], "John Wayne and Maureen O'Hara in a 1963 western comedy.", None),
    ("gullivers_travels1939", "gullivers-travels-1939", "Gulliver's Travels", 1939, ["Animation", "Family"], "English", US, "Dave Fleischer", [], "All", ["animated-movies", "family-entertainment"], "Fleischer Studios' 1939 animated feature based on Jonathan Swift's story.", "6-8"),
    ("20000LeaguesUndertheSea", "20000-leagues-under-the-sea-1916", "20,000 Leagues Under the Sea", 1916, ["Adventure", "Silent"], "Silent", US, "Stuart Paton", [], "9+", ["action-and-adventure"], "A 1916 silent adaptation of Jules Verne, known for early underwater photography.", None),
    ("lost_world", "the-lost-world-1925", "The Lost World", 1925, ["Adventure", "Silent"], "Silent", US, "Harry O. Hoyt", ["Wallace Beery", "Bessie Love"], "9+", ["action-and-adventure"], "The 1925 silent adaptation of Arthur Conan Doyle's novel, with stop-motion dinosaurs by Willis O'Brien.", None),
    ("BattleshipPotemkin", "battleship-potemkin", "Battleship Potemkin", 1925, ["Drama", "History", "Silent"], "Silent", "Soviet Union", "Sergei Eisenstein", [], "13+", ["drama"], "Sergei Eisenstein's 1925 film about the 1905 mutiny on the battleship Potemkin.", None),
    ("TheMostDangerousGame", "the-most-dangerous-game", "The Most Dangerous Game", 1932, ["Thriller", "Adventure"], "English", US, "Irving Pichel, Ernest B. Schoedsack", ["Joel McCrea", "Fay Wray"], "13+", ["mystery-and-thriller", "action-and-adventure"], "A shipwrecked hunter becomes the prey of a count on a remote island.", None),
    ("white_zombie", "white-zombie", "White Zombie", 1932, ["Horror"], "English", US, "Victor Halperin", ["Bela Lugosi"], "13+", ["mystery-and-thriller"], "Bela Lugosi in the 1932 horror film often described as the first zombie feature.", None),
    ("Hitch_Hiker", "the-hitch-hiker", "The Hitch-Hiker", 1953, ["Film noir", "Thriller"], "English", US, "Ida Lupino", ["Edmond O'Brien", "Frank Lovejoy"], "13+", ["mystery-and-thriller"], "Ida Lupino's 1953 noir about two friends forced to drive a killer across Mexico.", None),
    ("impact", "impact-1949", "Impact", 1949, ["Film noir"], "English", US, "Arthur Lubin", ["Brian Donlevy", "Ella Raines"], "13+", ["mystery-and-thriller", "drama"], "A 1949 noir about a businessman who survives his wife's murder plot.", None),
    ("Cyrano_DeBergerac", "cyrano-de-bergerac-1950", "Cyrano de Bergerac", 1950, ["Drama", "Romance"], "English", US, "Michael Gordon", ["José Ferrer"], "All", ["drama"], "José Ferrer in the 1950 film of Edmond Rostand's play.", None),
    ("Kilimanjaro", "the-snows-of-kilimanjaro", "The Snows of Kilimanjaro", 1952, ["Drama"], "English", US, "Henry King", ["Gregory Peck", "Susan Hayward", "Ava Gardner"], "13+", ["drama"], "Gregory Peck as a writer looking back on his life from a camp below Kilimanjaro. Based on Ernest Hemingway.", None),
    ("angel_and_the_badman", "angel-and-the-badman", "Angel and the Badman", 1947, ["Western"], "English", US, "James Edward Grant", ["John Wayne", "Gail Russell"], "9+", ["action-and-adventure", "drama"], "John Wayne as a gunfighter taken in by a Quaker family.", None),
    ("penny_serenade", "penny-serenade", "Penny Serenade", 1941, ["Drama", "Romance"], "English", US, "George Stevens", ["Irene Dunne", "Cary Grant"], "All", ["drama"], "Irene Dunne and Cary Grant in George Stevens's 1941 drama about a marriage.", None),
    ("Hitchcock_Secret_Agent", "secret-agent-1936", "Secret Agent", 1936, ["Thriller", "Spy"], "English", "United Kingdom", "Alfred Hitchcock", ["John Gielgud", "Madeleine Carroll", "Peter Lorre"], "13+", ["mystery-and-thriller"], "Alfred Hitchcock's 1936 spy thriller, loosely based on W. Somerset Maugham.", None),
    ("Haxan_tinted_and_subtitled", "haxan", "Häxan", 1922, ["Documentary", "Horror", "Silent"], "Silent (English subtitles)", "Sweden", "Benjamin Christensen", [], "16+", ["documentaries", "mystery-and-thriller"], "Benjamin Christensen's 1922 essay film on witchcraft, mixing documentary and staged scenes.", None),
    ("QuevivaMexico", "que-viva-mexico", "¡Que viva México!", 1931, ["Documentary"], "Spanish and English", "Mexico", "Sergei Eisenstein", [], "13+", ["documentaries"], "Footage Sergei Eisenstein shot in Mexico in 1930–31, later assembled into a film.", None),
    ("Santa_Fe_Trail_movie", "santa-fe-trail", "Santa Fe Trail", 1940, ["Western"], "English", US, "Michael Curtiz", ["Errol Flynn", "Olivia de Havilland"], "13+", ["action-and-adventure"], "Michael Curtiz's 1940 western with Errol Flynn and Olivia de Havilland.", None),
    ("CaptainKidd_", "captain-kidd-1945", "Captain Kidd", 1945, ["Adventure"], "English", US, "Rowland V. Lee", ["Charles Laughton", "Randolph Scott"], "9+", ["action-and-adventure"], "Charles Laughton as the pirate William Kidd.", None),
    ("Quicksand_clear", "quicksand-1950", "Quicksand", 1950, ["Film noir"], "English", US, "Irving Pichel", ["Mickey Rooney", "Peter Lorre"], "13+", ["mystery-and-thriller"], "Mickey Rooney as a mechanic whose small theft spirals out of control.", None),
    ("texas_terror_1935", "texas-terror", "Texas Terror", 1935, ["Western"], "English", US, "Robert N. Bradbury", ["John Wayne"], "9+", ["action-and-adventure"], "An early John Wayne western from 1935.", None),
    ("SagebrushTrail", "sagebrush-trail", "Sagebrush Trail", 1933, ["Western"], "English", US, "Armand Schaefer", ["John Wayne"], "9+", ["action-and-adventure"], "An early John Wayne western from 1933.", None),
    ("teenagers_from_outerspace", "teenagers-from-outer-space", "Teenagers from Outer Space", 1959, ["Science Fiction"], "English", US, "Tom Graeff", [], "13+", ["independent-films", "mystery-and-thriller"], "Tom Graeff's low-budget 1959 science-fiction film about an alien who rebels against his crew.", None),
    ("Killers_from_space", "killers-from-space", "Killers from Space", 1954, ["Science Fiction"], "English", US, "W. Lee Wilder", ["Peter Graves"], "13+", ["mystery-and-thriller"], "Peter Graves as a scientist who says he was abducted by aliens.", None),
    ("iron_mask", "the-iron-mask", "The Iron Mask", 1929, ["Adventure", "Silent"], "Silent", US, "Allan Dwan", ["Douglas Fairbanks"], "9+", ["action-and-adventure"], "Douglas Fairbanks as D'Artagnan in the 1929 sequel to The Three Musketeers.", None),
    ("mr_robinson_crusoe", "mr-robinson-crusoe", "Mr. Robinson Crusoe", 1932, ["Adventure", "Comedy"], "English", US, "A. Edward Sutherland", ["Douglas Fairbanks"], "All", ["action-and-adventure", "comedy"], "Douglas Fairbanks bets he can live on a desert island with nothing.", None),
]
for ident, slug, title, year, genres, lang, country, director, cast, age, extra, blurb, kids in F:
    ia(ident, slug, title, year, genres, lang, country, director, cast, "movie", age, CLASSIC + [c for c in extra if c != "family-entertainment"], blurb, kids=kids)

# Superman (Fleischer and Famous Studios, 1941–43), one multi-file item.
# Japoteurs and Jungle Drums are left out because of wartime racial caricature.
for file, slug, title, year, studio in [
    ("Superman.mp4", "superman-the-mad-scientist", "Superman: The Mad Scientist", 1941, "Fleischer Studios"),
    ("Superman-TheMechanicalMonsters.mp4", "superman-the-mechanical-monsters", "Superman: The Mechanical Monsters", 1941, "Fleischer Studios"),
    ("Superman - Billion Dollar Limited.mp4", "superman-billion-dollar-limited", "Superman: Billion Dollar Limited", 1942, "Fleischer Studios"),
    ("Superman-TheArcticGiant.mp4", "superman-the-arctic-giant", "Superman: The Arctic Giant", 1942, "Fleischer Studios"),
    ("Superman-TheBulleteers.mp4", "superman-the-bulleteers", "Superman: The Bulleteers", 1942, "Fleischer Studios"),
    ("Superman-TheMagneticTelescope.mp4", "superman-the-magnetic-telescope", "Superman: The Magnetic Telescope", 1942, "Fleischer Studios"),
    ("Superman-ElectricEarthquake.mp4", "superman-electric-earthquake", "Superman: Electric Earthquake", 1942, "Fleischer Studios"),
    ("Superman-Volcano.mp4", "superman-volcano", "Superman: Volcano", 1942, "Fleischer Studios"),
    ("Superman-TerrorOnTheMidway.mp4", "superman-terror-on-the-midway", "Superman: Terror on the Midway", 1942, "Fleischer Studios"),
    ("Superman-Showdown.mp4", "superman-showdown", "Superman: Showdown", 1942, "Famous Studios"),
    ("Superman-EleventhHour.mp4", "superman-eleventh-hour", "Superman: Eleventh Hour", 1942, "Famous Studios"),
    ("Superman-DestructionInc..mp4", "superman-destruction-inc", "Superman: Destruction, Inc.", 1942, "Famous Studios"),
    ("Superman-TheMummyStrikes.mp4", "superman-the-mummy-strikes", "Superman: The Mummy Strikes", 1943, "Famous Studios"),
    ("Superman-TheUndergroundWorld1943.mp4", "superman-the-underground-world", "Superman: The Underground World", 1943, "Famous Studios"),
    ("Superman-SecretAgent.mp4", "superman-secret-agent", "Superman: Secret Agent", 1943, "Famous Studios"),
]:
    ia("MaxFleischerSuperman", slug, title, year, ["Animation", "Action", "Short"], "English", US, studio, [], "short", "6+",
       CLASSIC + ["animated-movies", "short-films", "action-and-adventure"], f"{studio} Superman cartoon from {year}, about eight to ten minutes.", file=file, kids="6-8")

# Popeye (public-domain shorts)
for ident, slug, title, year in [
    ("Popeye_meetsSinbadtheSailor", "popeye-meets-sindbad-the-sailor", "Popeye the Sailor Meets Sindbad the Sailor", 1936),
    ("PopeyeTheSailorMeetsAliBabasFortyThieves1937", "popeye-meets-ali-babas-forty-thieves", "Popeye the Sailor Meets Ali Baba's Forty Thieves", 1937),
    ("Popeye_ThePanelessWindowWasher", "popeye-the-paneless-window-washer", "Popeye: The Paneless Window Washer", 1937),
    ("shuteye_popeye", "popeye-shuteye-popeye", "Popeye: Shuteye Popeye", 1952),
    ("Popeye_Floor_Flusher_1954", "popeye-floor-flusher", "Popeye: Floor Flusher", 1954),
    ("Popeye_Cooking_With_Gags_1954", "popeye-cooking-with-gags", "Popeye: Cooking with Gags", 1954),
    ("Popeye_Gopher_Spinach_1954", "popeye-gopher-spinach", "Popeye: Gopher Spinach", 1954),
    ("Popeye_Greek_Mirthology_1954", "popeye-greek-mirthology", "Popeye: Greek Mirthology", 1954),
    ("Popeye_BrideandGloom", "popeye-bride-and-gloom", "Popeye: Bride and Gloom", 1954),
    ("Popeye_Assault_and_Flattery_1956", "popeye-assault-and-flattery", "Popeye: Assault and Flattery", 1956),
    ("Popeye_forPresident", "popeye-for-president", "Popeye for President", 1956),
    ("Popeye_Nearlyweds", "popeye-nearlyweds", "Popeye: Nearlyweds", 1956),
]:
    studio = "Fleischer Studios" if year < 1942 else "Famous Studios"
    ia(ident, slug, title, year, ["Animation", "Comedy", "Short"], "English", US, studio, [], "short", "6+",
       CLASSIC + ["animated-movies", "short-films", "comedy"], f"{studio} Popeye cartoon from {year}.", kids="6-8")

# Betty Boop (Fleischer)
for ident, slug, title, year in [
    ("bb_minnie_the_moocher", "betty-boop-minnie-the-moocher", "Betty Boop: Minnie the Moocher", 1932),
    ("bb_snow_white", "betty-boop-snow-white", "Betty Boop: Snow White", 1933),
    ("bb_betty_in_blunderland", "betty-boop-betty-in-blunderland", "Betty Boop: Betty in Blunderland", 1934),
    ("Betty_Boops_Crazy_Inventions_1933", "betty-boops-crazy-inventions", "Betty Boop's Crazy Inventions", 1933),
    ("bb_parade_of_the_wooden_soldiers", "betty-boop-parade-of-the-wooden-soldiers", "Betty Boop: Parade of the Wooden Soldiers", 1933),
    ("Betty_Boop_Poor_Cinderella_1934", "betty-boop-poor-cinderella", "Betty Boop: Poor Cinderella", 1934),
    ("bb_and_grampy", "betty-boop-and-grampy", "Betty Boop and Grampy", 1935),
    ("bb_stop_that_noise", "betty-boop-stop-that-noise", "Betty Boop: Stop That Noise", 1935),
]:
    ia(ident, slug, title, year, ["Animation", "Comedy", "Short"], "English", US, "Dave Fleischer", [], "short", "9+",
       CLASSIC + ["animated-movies", "short-films", "comedy"], f"Fleischer Studios Betty Boop cartoon from {year}.", kids="9-12")

# Other classic cartoons
ia("RudolphTheRed-nosedReindeer1948", "rudolph-the-red-nosed-reindeer-1948", "Rudolph the Red-Nosed Reindeer", 1948, ["Animation", "Short", "Holiday"], "English", US, "Max Fleischer", [], "short", "All",
   CLASSIC + ["animated-movies", "short-films"], "Max Fleischer's 1948 cartoon of the Rudolph story, made for the Montgomery Ward department store.", kids="preschool")
ia("SantasSuprise", "santas-surprise", "Santa's Surprise", 1947, ["Animation", "Short", "Holiday"], "English", US, "Seymour Kneitel", [], "short", "All",
   CLASSIC + ["animated-movies", "short-films"], "Famous Studios Noveltoon from 1947 in which children from around the world tidy Santa's workshop.", kids="preschool")
ia("JackFrost_", "jack-frost-1934", "Jack Frost", 1934, ["Animation", "Short"], "English", US, "Ub Iwerks", [], "short", "All",
   CLASSIC + ["animated-movies", "short-films"], "Ub Iwerks ComiColor cartoon from 1934 about a bear cub who won't hibernate.", kids="preschool")

# Educational and nature films (Prelinger Archives and other public-domain classroom films)
for ident, slug, title, year, genres, director, cats, blurb, kids in [
    ("Hareandt1947", "the-hare-and-the-tortoise-1947", "The Hare and the Tortoise", 1947, ["Educational", "Short"], "Encyclopaedia Britannica Films", ["educational-movies", "short-films", "nature-and-wildlife"], "A 1947 Encyclopaedia Britannica classroom film telling Aesop's fable with live animals.", "preschool"),
    ("ThreeLit1938", "three-little-kittens-1938", "Three Little Kittens", 1938, ["Educational", "Short"], "ERPI Classroom Films", ["educational-movies", "short-films", "nature-and-wildlife"], "A 1938 classroom film following three kittens, made by ERPI Classroom Films.", "preschool"),
    ("Adventur1948", "adventures-of-junior-raindrop", "The Adventures of Junior Raindrop", 1948, ["Educational", "Animation", "Short"], "U.S. Forest Service", ["educational-movies", "short-films", "science-and-technology", "animated-movies"], "A 1948 U.S. Forest Service film about the water cycle and why forests matter.", "6-8"),
    ("Dayatthe1928", "a-day-at-the-river-1928", "A Day at the River", 1928, ["Educational", "Nature", "Silent", "Short"], "DeVry School Films", ["educational-movies", "short-films", "nature-and-wildlife"], "A 1928 silent nature-study lesson filmed along a river.", "6-8"),
    ("Billieth1956", "billie-the-buffalo-baby", "Billie, the Buffalo Baby", 1956, ["Educational", "Nature", "Short"], "Frith Films", ["educational-movies", "short-films", "nature-and-wildlife"], "A 1956 classroom film about a young bison.", "preschool"),
    ("Chinooks1940", "chinooks-children", "Chinook's Children", 1940, ["Educational", "Nature", "Short"], "Pictoreels", ["educational-movies", "short-films", "nature-and-wildlife"], "A 1940s nature film on the life cycle of Chinook salmon.", "6-8"),
    ("BirdsofP1938", "birds-of-prey-1938", "Birds of Prey", 1938, ["Educational", "Nature", "Short"], "ERPI Classroom Films", ["educational-movies", "short-films", "nature-and-wildlife"], "A 1938 classroom film about hawks, owls and other birds of prey.", "6-8"),
    ("Animalsi1937", "animals-in-modern-life", "Animals in Modern Life", 1937, ["Educational", "Nature", "Short"], "ERPI Classroom Films", ["educational-movies", "short-films", "nature-and-wildlife"], "A 1937 classroom film about animals and people.", None),
    ("PrivateL1947", "the-private-life-of-a-cat", "The Private Life of a Cat", 1947, ["Documentary", "Nature", "Short"], "Alexander Hammid, Maya Deren", ["documentaries", "short-films", "nature-and-wildlife", "independent-films"], "Alexander Hammid and Maya Deren's 1947 film of a cat giving birth and raising her kittens.", None),
    ("Heritage1963", "heritage-of-splendor", "Heritage of Splendor", 1963, ["Documentary", "Nature", "Short"], "Alfred Higgins Productions", ["documentaries", "short-films", "nature-and-wildlife"], "A 1963 conservation film about America's landscapes and litter, narrated by Ronald Reagan.", None),
]:
    ia(ident, slug, title, year, genres, "English" if "Silent" not in genres else "Silent", US, director, [], "short", "All", cats, blurb, kids=kids)

# NASA films
for ident, slug, title, year, blurb in [
    ("highlights_1965_1", "nasa-highlights-1965-part-1", "Highlights 1965: A Progress Report (Part I)", 1965, "NASA's 1965 progress report on the American space programme, part one."),
    ("WithinThisDecade", "within-this-decade-america-in-space", "Within This Decade: America in Space", 1969, "A 1969 NASA film on the U.S. space programme leading up to the Moon landing."),
    ("TheKnowledgeBank", "space-in-the-70s-the-knowledge-bank", "Space in the 70s: The Knowledge Bank", 1971, "A 1971 NASA film on what the space programme had added to science."),
    ("Skylab_TheFirst40Days", "skylab-the-first-40-days", "Skylab: The First 40 Days", 1973, "NASA's film of the first crewed mission to the Skylab space station and its repairs in orbit."),
    ("Apollo17-OnTheShouldersOfGiants", "apollo-17-on-the-shoulders-of-giants", "Apollo 17: On the Shoulders of Giants", 1973, "NASA's documentary of Apollo 17, the last crewed Moon landing of the Apollo programme."),
    ("TheApollo-soyuzMission", "the-apollo-soyuz-mission", "The Apollo-Soyuz Mission", 1975, "NASA's film of the 1975 joint mission in which American and Soviet spacecraft docked in orbit."),
]:
    ia(ident, slug, title, year, ["Documentary", "Science"], "English", US, "NASA", [], "documentary", "All",
       ["documentaries", "educational-movies", "science-and-technology", "international-movies"], blurb, kids="9-12")

# Classic TV episodes
TV = ["international-movies", "classic-cinema", "tv-series"]
for ident, slug, title, year, genres, director, cast, age, cats, blurb in [
    ("Beverly_Hillbillies_Ep01_The_Clampetts_Strike_Oil", "the-beverly-hillbillies-s1-e1", "The Beverly Hillbillies S1 E1: The Clampetts Strike Oil", 1962, ["Comedy", "Series"], "Paul Henning (creator)", ["Buddy Ebsen", "Irene Ryan", "Donna Douglas", "Max Baer Jr."], "All", ["comedy"], "The pilot: Jed Clampett strikes oil and the family moves to Beverly Hills."),
    ("Beverly_Hillbillies_Ep02_Getting_Settled", "the-beverly-hillbillies-s1-e2", "The Beverly Hillbillies S1 E2: Getting Settled", 1962, ["Comedy", "Series"], "Paul Henning (creator)", ["Buddy Ebsen", "Irene Ryan", "Donna Douglas", "Max Baer Jr."], "All", ["comedy"], "The Clampetts settle into their Beverly Hills mansion."),
    ("Beverly_Hillbillies_Ep06_Trick_Or_Treat", "the-beverly-hillbillies-s1-e6", "The Beverly Hillbillies S1 E6: Trick or Treat", 1962, ["Comedy", "Series"], "Paul Henning (creator)", ["Buddy Ebsen", "Irene Ryan", "Donna Douglas", "Max Baer Jr."], "All", ["comedy"], "The Clampetts meet Halloween in the city."),
    ("Beverly_Hillbillies_Ep07_The_Servants", "the-beverly-hillbillies-s1-e7", "The Beverly Hillbillies S1 E7: The Servants", 1962, ["Comedy", "Series"], "Paul Henning (creator)", ["Buddy Ebsen", "Irene Ryan", "Donna Douglas", "Max Baer Jr."], "All", ["comedy"], "The family tries to work out what to do with household servants."),
    ("Beverly_Hillbillies_Ep13_Home_For_Christmas", "the-beverly-hillbillies-s1-e13", "The Beverly Hillbillies S1 E13: Home for Christmas", 1962, ["Comedy", "Series"], "Paul Henning (creator)", ["Buddy Ebsen", "Irene Ryan", "Donna Douglas", "Max Baer Jr."], "All", ["comedy"], "The Clampetts' first Christmas in Beverly Hills."),
    ("TLS_Lucy_Gets_A_Roommate", "the-lucy-show-lucy-gets-a-roommate", "The Lucy Show: Lucy Gets a Roommate", 1962, ["Comedy", "Series"], "See the source record", ["Lucille Ball", "Vivian Vance"], "All", ["comedy"], "An episode of The Lucy Show with Lucille Ball and Vivian Vance."),
    ("TLS_Little_Old_Lady", "the-lucy-show-little-old-lady", "The Lucy Show: Little Old Lady", 1962, ["Comedy", "Series"], "See the source record", ["Lucille Ball", "Vivian Vance"], "All", ["comedy"], "An episode of The Lucy Show with Lucille Ball and Vivian Vance."),
    ("TLS_Lucy_And_Viv_Put_In_A_Shower", "the-lucy-show-lucy-and-viv-put-in-a-shower", "The Lucy Show: Lucy and Viv Put in a Shower", 1962, ["Comedy", "Series"], "See the source record", ["Lucille Ball", "Vivian Vance"], "All", ["comedy"], "An episode of The Lucy Show with Lucille Ball and Vivian Vance."),
    ("Bonanza-DeathOnSunMountain", "bonanza-death-on-sun-mountain", "Bonanza: Death on Sun Mountain", 1959, ["Western", "Series"], "See the source record", ["Lorne Greene", "Pernell Roberts", "Dan Blocker", "Michael Landon"], "9+", ["action-and-adventure", "drama"], "An early Bonanza episode with the Cartwright family."),
    ("SherlockHolmes-TheCaseoftheShyBallerina", "sherlock-holmes-1954-the-shy-ballerina", "Sherlock Holmes (1954): The Case of the Shy Ballerina", 1954, ["Mystery", "Series"], "Sheldon Reynolds (producer)", ["Ronald Howard", "H. Marion Crawford"], "All", ["mystery-and-thriller"], "Ronald Howard as Holmes in the 1954 television series."),
    ("SherlockHolmes-TheCaseofLadyBeryl", "sherlock-holmes-1954-the-case-of-lady-beryl", "Sherlock Holmes (1954): The Case of Lady Beryl", 1954, ["Mystery", "Series"], "Sheldon Reynolds (producer)", ["Ronald Howard", "H. Marion Crawford"], "All", ["mystery-and-thriller"], "Ronald Howard as Holmes in the 1954 television series."),
    ("SherlockHolmes-TheCaseoftheCunninghamHeritage", "sherlock-holmes-1954-the-cunningham-heritage", "Sherlock Holmes (1954): The Case of the Cunningham Heritage", 1954, ["Mystery", "Series"], "Sheldon Reynolds (producer)", ["Ronald Howard", "H. Marion Crawford"], "All", ["mystery-and-thriller"], "Ronald Howard as Holmes in the 1954 television series."),
    ("Andy-Griffith-Show_Andy-Discovers-America", "the-andy-griffith-show-andy-discovers-america", "The Andy Griffith Show S3 E23: Andy Discovers America", 1963, ["Comedy", "Series"], "See the source record", ["Andy Griffith", "Ron Howard", "Don Knotts"], "All", ["comedy"], "Andy tries to get Opie interested in American history."),
    ("Cisco_Kid_-_Buried_Treasure", "the-cisco-kid-buried-treasure", "The Cisco Kid: Buried Treasure", 1950, ["Western", "Series"], "See the source record", ["Duncan Renaldo", "Leo Carrillo"], "All", ["action-and-adventure"], "An episode of The Cisco Kid, one of the first television series filmed in colour."),
    ("Topper-HenriettaSellsTheHouse", "topper-henrietta-sells-the-house", "Topper: Henrietta Sells the House", 1953, ["Comedy", "Series"], "See the source record", ["Leo G. Carroll", "Anne Jeffreys", "Robert Sterling"], "All", ["comedy"], "An episode of the 1953 television comedy Topper."),
    ("Mama1950", "i-remember-mama-mamas-bad-day", "I Remember Mama: Mama's Bad Day", 1950, ["Drama", "Series"], "See the source record", ["Peggy Wood"], "All", ["drama"], "An episode of the live television family drama Mama, from 1950."),
    ("TheChristmasCarolastoldbyVincentPrice", "the-christmas-carol-1949-vincent-price", "The Christmas Carol (1949)", 1949, ["Drama", "Holiday"], "See the source record", ["Vincent Price", "Taylor Holmes"], "All", ["drama"], "A 1949 television version of Dickens's story, introduced and narrated by Vincent Price."),
    ("enter_the_lone_ranger", "enter-the-lone-ranger", "Enter the Lone Ranger", 1949, ["Western", "Series"], "George B. Seitz Jr.", ["Clayton Moore", "Jay Silverheels"], "9+", ["action-and-adventure"], "The opening episodes of the 1949 Lone Ranger television series, presented together."),
]:
    ia(ident, slug, title, year, genres, "English", US, director, cast, "series", age, TV + cats, blurb)
