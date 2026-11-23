"""Build the demonstration catalogue from verified public-domain and CC records.

The Internet Archive metadata and licence URLs were checked on 2026-11-23.
This script does not invent titles. Playback URLs point at the Archive's own
player or a file on that same item.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from urllib.parse import quote

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import additions  # noqa: E402
from additions_build import add_verified_additions  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
NS = uuid.UUID("6f9c0b2e-1a4d-4e3a-9c11-sospana".replace("-sospana", "-000000000001")[:36])


def uid(name: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "https://sospana.cinema/" + name))


def download(identifier: str, filename: str) -> str:
    return f"https://archive.org/download/{identifier}/{quote(filename, safe='')}"


def embed(identifier: str) -> str:
    return f"https://archive.org/embed/{identifier}"


def poster(identifier: str) -> str:
    return f"https://archive.org/services/img/{identifier}"


def item(identifier: str) -> str:
    return f"https://archive.org/details/{identifier}"


CATEGORIES = [
    ("international-movies", "International Movies", "Verified films and shorts from every country in the catalogue."),
    ("african-cinema", "African Cinema", "African films, series and shorts played from their rights holders' own channels or from verified open-licence records."),
    ("south-african-movies", "South African Movies", "South African films, series and shorts played from their rights holders' own official channels."),
    ("kids-movies", "Kids Movies", "Titles a person reviewed by hand before they were published in Kids Cinema."),
    ("cartoons", "Kids Cartoons", "Openly licensed cartoons a person approved for children."),
    ("animated-movies", "Animated Movies", "Animated films and shorts with a verified licence, including titles that are not for children."),
    ("anime", "Anime", "Anime played from the rights holder's official channel. Region limits set by the rights holder apply."),
    ("tv-series", "TV Series", "Series episodes from official channels and public-domain television."),
    ("documentaries", "Documentaries", "Documentaries with a verified licence and an authorized player."),
    ("educational-movies", "Educational Movies", "Films kept for learning, with a verified licence."),
    ("nature-and-wildlife", "Nature and Wildlife", "Nature films from official free releases and public-domain classroom films."),
    ("science-and-technology", "Science and Technology", "Science films with a verified licence."),
    ("classic-cinema", "Classic Cinema", "Older films whose source record carries a public-domain mark or an equivalent statement."),
    ("family-entertainment", "Family Entertainment", "Titles approved for family viewing after a manual review."),
    ("independent-films", "Independent Films", "Independently made films with a verified public-domain or open licence."),
    ("short-films", "Short Films", "Films and open movies under about 40 minutes."),
    ("comedy", "Comedy", "Comedies with a verified licence."),
    ("action-and-adventure", "Action and Adventure", "Action and adventure films with a verified licence."),
    ("drama", "Drama", "Dramas with a verified licence."),
    ("mystery-and-thriller", "Mystery and Thriller", "Mysteries, thrillers and horror films with a verified licence."),
    ("kids-preschool", "Preschool", "Hand-reviewed titles for the youngest children."),
    ("kids-nursery-rhymes", "Nursery Rhymes", "Nursery rhymes with a verified licence. None are in this demonstration yet."),
    ("kids-educational-cartoons", "Educational Cartoons", "Educational cartoons a person approved for children. None are in this demonstration yet."),
    ("kids-animated-movies", "Animated Movies", "Animated titles approved for Kids Cinema."),
    ("kids-adventure-cartoons", "Adventure Cartoons", "Adventure cartoons approved for children."),
    ("kids-african-stories", "African Children's Stories", "African children's stories with a verified licence. None are in this demonstration yet."),
    ("kids-science", "Science for Kids", "Science films approved for children."),
    ("kids-nature", "Nature for Kids", "Nature films approved for children. None are in this demonstration yet."),
    ("kids-family", "Family Movies", "Films approved for family viewing."),
    ("kids-learning", "Learning and Discovery", "Learning films approved for children or family viewing."),
]

SOURCES = [
    {
        "slug": "internet-archive",
        "providerName": "Internet Archive",
        "websiteUrl": "https://archive.org",
        "providerType": "public-library",
        "apiStatus": "official-search-api",
        "termsReference": "https://archive.org/about/terms.php",
    },
    {
        "slug": "blender-foundation",
        "providerName": "Blender Foundation",
        "websiteUrl": "https://www.blender.org",
        "providerType": "rights-holder",
        "apiStatus": "open-licence-pages",
        "termsReference": "https://creativecommons.org/licenses/by/3.0/",
    },
    {
        "slug": "national-archives",
        "providerName": "U.S. National Archives",
        "websiteUrl": "https://www.archives.gov",
        "providerType": "public-institution",
        "apiStatus": "item-on-internet-archive",
        "termsReference": "https://creativecommons.org/publicdomain/zero/1.0/",
    },
    {
        "slug": "youtube",
        "providerName": "YouTube (official embeds)",
        "websiteUrl": "https://www.youtube.com",
        "providerType": "official-embed-platform",
        "apiStatus": "oembed-and-watch-page-checked",
        "termsReference": "https://www.youtube.com/t/terms",
    },
]
SOURCES += [
    {
        "slug": slug,
        "providerName": name,
        "websiteUrl": f"https://www.youtube.com/channel/{channel}",
        "providerType": "rights-holder",
        "apiStatus": "official-youtube-channel",
        "termsReference": site,
    }
    for slug, (name, channel, _about, site) in additions.YT_HOLDERS.items()
]


def sub(identifier: str, filename: str, language: str, label: str) -> dict:
    return {"language": language, "label": label, "url": download(identifier, filename)}


def add(rows: list, **movie) -> None:
    rows.append(movie)


def build() -> dict:
    rows: list[dict] = []
    ia = "internet-archive"
    # identifier, mp4 filename or None, extra kwargs folded below via helper calls

    def film(
        slug: str,
        title: str,
        year: int,
        runtime: int,
        genres: list[str],
        language: str,
        country: str,
        director: str,
        cast: list[str],
        content_type: str,
        age: str,
        description: str,
        categories: list[str],
        identifier: str,
        licence_type: str,
        licence_url: str,
        created: str,
        mp4: str | None = None,
        subs: list | None = None,
        featured: bool = False,
        review: dict | None = None,
        note: str | None = None,
        rights_holder: str = "See the source record",
        holder_slug: str = ia,
        quality_note: str | None = None,
    ) -> None:
        sources = [
            {
                "providerSlug": ia,
                "playbackType": "embed",
                "url": embed(identifier),
                "licenceType": licence_type,
                "licenceEvidenceUrl": licence_url,
                "sourceRecordUrl": item(identifier),
                "licenceTerritories": ["WORLD"],
                "rightsVerified": True,
                "playbackStatus": "available",
                "lastVerifiedAt": "2026-11-23",
                "rightsHolder": rights_holder,
                "rightsHolderSource": holder_slug,
                "subtitles": [],
                "qualityNote": "Internet Archive's own player for this item.",
            }
        ]
        if mp4:
            sources.insert(
                0,
                {
                    "providerSlug": ia,
                    "playbackType": "mp4",
                    "url": download(identifier, mp4),
                    "licenceType": licence_type,
                    "licenceEvidenceUrl": licence_url,
                    "sourceRecordUrl": item(identifier),
                    "licenceTerritories": ["WORLD"],
                    "rightsVerified": True,
                    "playbackStatus": "available",
                    "lastVerifiedAt": "2026-11-23",
                    "rightsHolder": rights_holder,
                    "rightsHolderSource": holder_slug,
                    "subtitles": subs or [],
                    "qualityNote": quality_note
                    or "Direct file published on the same Internet Archive item.",
                },
            )
        add(
            rows,
            slug=slug,
            title=title,
            description=description,
            releaseYear=year,
            runtimeSeconds=runtime,
            genres=genres,
            language=language,
            country=country,
            director=director,
            cast=cast,
            contentType=content_type,
            ageRating=age,
            posterUrl=poster(identifier),
            backdropUrl=poster(identifier),
            trailerUrl=None,
            categories=categories,
            featured=featured,
            published=True,
            createdAt=created + "T12:00:00Z",
            updatedAt="2026-11-23T12:00:00Z",
            archiveIdentifier=identifier,
            note=note,
            sources=sources,
            review=review,
        )

    small = "Internet Archive's smaller MPEG-4 derivative of this item. The archive player is also linked."
    auto = "English (automatic captions supplied with the archive item)"

    film(
        "sherlock-jr",
        "Sherlock Jr.",
        1924,
        2674,
        ["Comedy", "Silent"],
        "Silent",
        "United States",
        "Buster Keaton",
        ["Buster Keaton", "Kathryn McGuire", "Joe Keaton"],
        "movie",
        "All",
        "Buster Keaton plays a projectionist who dreams himself into the film on screen. Silent comedy, released in 1924. The archive item carries a Public Domain Mark.",
        ["international-movies", "classic-cinema", "comedy", "short-films"],
        "sherlock-jr-1924-tmdb992",
        "public-domain-mark",
        "https://creativecommons.org/publicdomain/mark/1.0/",
        "2026-10-22",
        mp4="Sherlock Jr. (1924).mp4",
        featured=True,
    )
    film(
        "the-general",
        "The General",
        1926,
        4039,
        ["Comedy", "Action", "Silent"],
        "Silent",
        "United States",
        "Buster Keaton, Clyde Bruckman",
        ["Buster Keaton", "Marion Mack"],
        "movie",
        "All",
        "Buster Keaton is a railway engineer who chases a stolen locomotive during the American Civil War. Silent comedy. The archive item is marked public domain.",
        ["international-movies", "classic-cinema", "comedy", "action-and-adventure"],
        "TheGeneral",
        "public-domain",
        "http://creativecommons.org/licenses/publicdomain/",
        "2026-10-25",
        mp4="The_General_512kb.mp4",
        quality_note=small,
        featured=True,
    )
    film(
        "steamboat-bill-jr",
        "Steamboat Bill, Jr.",
        1928,
        4148,
        ["Comedy", "Silent"],
        "Silent",
        "United States",
        "Charles Reisner, Buster Keaton",
        ["Buster Keaton", "Ernest Torrence", "Marion Byron"],
        "movie",
        "All",
        "A riverboat captain's son has to prove himself when a storm hits the town. Buster Keaton silent comedy from 1928. The archive item is marked public domain.",
        ["international-movies", "classic-cinema", "comedy"],
        "SteamboatBillJr",
        "public-domain",
        "http://creativecommons.org/licenses/publicdomain/",
        "2026-10-24",
        mp4="Steamboat_Bill.Jr_512kb.mp4",
        quality_note=small,
    )
    film(
        "safety-last",
        "Safety Last!",
        1923,
        4433,
        ["Comedy", "Silent"],
        "Silent",
        "United States",
        "Fred C. Newmeyer, Sam Taylor",
        ["Harold Lloyd", "Mildred Davis"],
        "movie",
        "All",
        "Harold Lloyd's store clerk ends up climbing the outside of a tall building. Silent comedy from 1923. Playback is the Internet Archive player for an item with a Public Domain Mark.",
        ["international-movies", "classic-cinema", "comedy", "action-and-adventure"],
        "safety-last-1923-tmdb22596",
        "public-domain-mark",
        "https://creativecommons.org/publicdomain/mark/1.0/",
        "2026-10-23",
        note="The direct file on this item is very large, so Sospana Cinema uses the archive player and does not rehost that file.",
    )
    film(
        "a-trip-to-the-moon",
        "A Trip to the Moon",
        1902,
        762,
        ["Fantasy", "Science Fiction", "Silent", "Short"],
        "Silent",
        "France",
        "Georges Méliès",
        ["Georges Méliès"],
        "short",
        "All",
        "Georges Méliès's 1902 fantasy of astronomers fired to the moon. About 13 minutes. The archive item carries a Public Domain Mark.",
        ["international-movies", "classic-cinema", "short-films", "family-entertainment", "educational-movies", "kids-family", "kids-learning", "kids-movies"],
        "a-trip-to-the-moon-le-voyage-dans-la-lune-1902",
        "public-domain-mark",
        "https://creativecommons.org/publicdomain/mark/1.0/",
        "2026-10-20",
        mp4="A Trip to the moon (Le voyage dans la lune) (1902).mp4",
        review={
            "status": "approved",
            "suitability": "family",
            "notes": "Manual review on 2026-11-23. A 1902 silent fantasy of about 13 minutes. The moon landing is startling and a comic explosion is shown. Approved for family viewing. Not published for preschool.",
            "reviewedAt": "2026-11-23",
        },
    )
    film(
        "the-great-train-robbery",
        "The Great Train Robbery",
        1903,
        692,
        ["Action", "Western", "Silent", "Short"],
        "Silent",
        "United States",
        "Edwin S. Porter",
        ["Gilbert M. Anderson"],
        "short",
        "6+",
        "Edwin S. Porter's 1903 short about a train hold-up. About 12 minutes. People are shown being shot. The archive item carries a Public Domain Mark.",
        ["international-movies", "classic-cinema", "short-films", "action-and-adventure"],
        "the-great-train-robbery-1903",
        "public-domain-mark",
        "https://creativecommons.org/publicdomain/mark/1.0/",
        "2026-10-21",
        mp4="The Great Train Robbery (1903).mp4",
    )
    film(
        "nosferatu",
        "Nosferatu",
        1922,
        5224,
        ["Horror", "Silent"],
        "Silent",
        "Germany",
        "F. W. Murnau",
        ["Max Schreck", "Gustav von Wangenheim", "Greta Schröder"],
        "movie",
        "13+",
        "F. W. Murnau's silent vampire film, premiered in 1922, with Max Schreck as Count Orlok. The archive item carries a Public Domain Mark.",
        ["international-movies", "classic-cinema", "mystery-and-thriller"],
        "nosferatu.-1922",
        "public-domain-mark",
        "https://creativecommons.org/publicdomain/mark/1.0/",
        "2026-10-26",
        mp4="Nosferatu.1922.ia.mp4",
        quality_note="Internet Archive's derived MPEG-4 for this item, about 457 MB. The archive player is also linked.",
        featured=True,
    )
    film(
        "the-cabinet-of-dr-caligari",
        "The Cabinet of Dr. Caligari",
        1920,
        3061,
        ["Horror", "Silent"],
        "Silent",
        "Germany",
        "Robert Wiene",
        ["Werner Krauss", "Conrad Veidt", "Friedrich Feher"],
        "movie",
        "13+",
        "Robert Wiene's 1920 expressionist horror film about a hypnotist and a somnambulist. This archive copy runs about 51 minutes and is marked public domain.",
        ["international-movies", "classic-cinema", "mystery-and-thriller"],
        "DasKabinettdesDoktorCaligariTheCabinetofDrCaligari",
        "public-domain",
        "http://creativecommons.org/licenses/publicdomain/",
        "2026-10-27",
        mp4="The_Cabinet_of_Dr._Caligari_512kb.mp4",
        quality_note=small,
        featured=True,
    )
    film(
        "metropolis",
        "Metropolis",
        1927,
        8937,
        ["Science Fiction", "Drama", "Silent"],
        "Silent",
        "Germany",
        "Fritz Lang",
        ["Alfred Abel", "Brigitte Helm", "Gustav Fröhlich"],
        "movie",
        "All",
        "Fritz Lang's 1927 science-fiction film about a divided city, from a script by Thea von Harbou. Playback is the Internet Archive player for an item with a Public Domain Mark and English titles.",
        ["international-movies", "classic-cinema", "drama"],
        "metropolis-1927-english-titles",
        "public-domain-mark",
        "https://creativecommons.org/publicdomain/mark/1.0/",
        "2026-10-28",
        note="The direct file on this item is about 1.5 GB, so Sospana Cinema uses the archive player and does not rehost that file. Later restorations of Metropolis can have their own rights. This entry is the archive item, not a commercial restoration.",
        featured=True,
    )
    film(
        "the-phantom-of-the-opera",
        "The Phantom of the Opera",
        1925,
        6165,
        ["Horror", "Silent"],
        "Silent",
        "United States",
        "Rupert Julian",
        ["Lon Chaney", "Mary Philbin", "Norman Kerry"],
        "movie",
        "13+",
        "The 1925 silent film of The Phantom of the Opera, with Lon Chaney. Playback is the Internet Archive player. The item is marked with a Public Domain Mark and describes itself as the original 1925 edit.",
        ["international-movies", "classic-cinema", "mystery-and-thriller"],
        "PhantomOfTheOpera1925HD",
        "public-domain-mark",
        "https://creativecommons.org/publicdomain/mark/1.0/",
        "2026-10-31",
        note="The direct file on this item is about 1.8 GB, so Sospana Cinema uses the archive player and does not rehost that file.",
    )
    film(
        "intolerance",
        "Intolerance",
        1916,
        10587,
        ["Drama", "Silent"],
        "Silent",
        "United States",
        "D. W. Griffith",
        ["Mae Marsh", "Robert Harron", "Lillian Gish"],
        "movie",
        "All",
        "D. W. Griffith's 1916 silent epic telling four stories about intolerance. This archive copy runs about 176 minutes and is marked public domain.",
        ["international-movies", "classic-cinema", "drama"],
        "Intolerance",
        "public-domain",
        "http://creativecommons.org/licenses/publicdomain/",
        "2026-10-29",
        mp4="Intolerance_512kb.mp4",
        quality_note=small,
    )
    film(
        "nanook-of-the-north",
        "Nanook of the North",
        1922,
        4712,
        ["Documentary", "Silent"],
        "Silent",
        "United States",
        "Robert J. Flaherty",
        ["Allakariallak"],
        "documentary",
        "All",
        "Robert J. Flaherty's 1922 documentary about an Inuit family in northern Quebec. Some scenes were staged. The archive item carries a Public Domain Mark. It is not an African film.",
        ["documentaries", "classic-cinema", "international-movies"],
        "nanook-of-the-north-1922-tmdb669",
        "public-domain-mark",
        "https://creativecommons.org/publicdomain/mark/1.0/",
        "2026-10-30",
        mp4="Nanook of the North (1922).mp4",
    )
    film(
        "his-girl-friday",
        "His Girl Friday",
        1940,
        5505,
        ["Comedy", "Romance"],
        "English",
        "United States",
        "Howard Hawks",
        ["Cary Grant", "Rosalind Russell", "Ralph Bellamy"],
        "movie",
        "All",
        "Howard Hawks's 1940 newsroom comedy with Cary Grant and Rosalind Russell. The archive item is marked public domain.",
        ["international-movies", "classic-cinema", "comedy"],
        "his_girl_friday",
        "public-domain",
        "http://creativecommons.org/licenses/publicdomain/",
        "2026-11-03",
        mp4="his_girl_friday.mp4",
        subs=[sub("his_girl_friday", "his_girl_friday.asr.srt", "en", auto)],
        featured=True,
    )
    film(
        "nothing-sacred",
        "Nothing Sacred",
        1937,
        4450,
        ["Comedy"],
        "English",
        "United States",
        "William A. Wellman",
        ["Carole Lombard", "Fredric March"],
        "movie",
        "All",
        "A 1937 comedy with Carole Lombard and Fredric March about a newspaper and a woman said to be dying. The archive item is marked public domain.",
        ["international-movies", "classic-cinema", "comedy"],
        "NothingSacred",
        "public-domain",
        "http://creativecommons.org/licenses/publicdomain/",
        "2026-11-02",
        mp4="NothingSacred.mp4",
    )
    film(
        "my-man-godfrey",
        "My Man Godfrey",
        1936,
        5687,
        ["Comedy"],
        "English",
        "United States",
        "Gregory La Cava",
        ["William Powell", "Carole Lombard"],
        "movie",
        "All",
        "A 1936 comedy with William Powell and Carole Lombard. A socialite hires a man she met during a scavenger hunt as the family butler. The archive item is marked public domain.",
        ["international-movies", "classic-cinema", "comedy"],
        "MyManGodfrey1936",
        "public-domain",
        "http://creativecommons.org/licenses/publicdomain/",
        "2026-11-01",
        mp4="MyManGodfrey1936.mp4",
    )
    film(
        "charade",
        "Charade",
        1963,
        6817,
        ["Mystery", "Comedy", "Romance"],
        "English",
        "United States",
        "Stanley Donen",
        ["Cary Grant", "Audrey Hepburn", "Walter Matthau"],
        "movie",
        "13+",
        "Stanley Donen's 1963 mystery comedy set in Paris, with Cary Grant and Audrey Hepburn. The film is widely treated as public domain in the United States because of a defective copyright notice. Playback is the Internet Archive player for an item with a Public Domain Mark.",
        ["international-movies", "classic-cinema", "comedy", "mystery-and-thriller"],
        "charade-1963-4k",
        "public-domain-mark",
        "https://creativecommons.org/publicdomain/mark/1.0/",
        "2026-11-15",
        note="The file on this item is extremely large, so Sospana Cinema uses the archive player and does not rehost it. A restored or upscaled copy can add new rights even when the 1963 film is in the public domain. This entry is the archive item.",
        featured=True,
    )
    film(
        "detour",
        "Detour",
        1945,
        4058,
        ["Drama", "Thriller"],
        "English",
        "United States",
        "Edgar G. Ulmer",
        ["Tom Neal", "Ann Savage"],
        "movie",
        "13+",
        "Edgar G. Ulmer's 1945 film noir. A pianist hitchhiking to California is pulled into a crime. The archive item carries a Public Domain Mark.",
        ["international-movies", "classic-cinema", "drama", "mystery-and-thriller", "independent-films"],
        "Detour1945_201808",
        "public-domain-mark",
        "https://creativecommons.org/publicdomain/mark/1.0/",
        "2026-11-05",
        mp4="Detour (1945).mp4",
    )
    film(
        "the-stranger",
        "The Stranger",
        1946,
        5643,
        ["Thriller", "Drama"],
        "English",
        "United States",
        "Orson Welles",
        ["Orson Welles", "Edward G. Robinson", "Loretta Young"],
        "movie",
        "13+",
        "Orson Welles's 1946 thriller. A war-crimes investigator looks for a Nazi hiding in a Connecticut town. The archive item carries a Public Domain Mark.",
        ["international-movies", "classic-cinema", "drama", "mystery-and-thriller"],
        "the-stranger-1946",
        "public-domain-mark",
        "https://creativecommons.org/publicdomain/mark/1.0/",
        "2026-11-06",
        mp4="The Stranger (1946).mp4",
    )
    film(
        "scarlet-street",
        "Scarlet Street",
        1945,
        6086,
        ["Drama", "Thriller"],
        "English",
        "United States",
        "Fritz Lang",
        ["Edward G. Robinson", "Joan Bennett", "Dan Duryea"],
        "movie",
        "13+",
        "Fritz Lang's 1945 noir with Edward G. Robinson, Joan Bennett and Dan Duryea. The archive item is marked public domain.",
        ["international-movies", "classic-cinema", "drama", "mystery-and-thriller"],
        "ScarletStreet",
        "public-domain",
        "http://creativecommons.org/licenses/publicdomain/",
        "2026-11-07",
        mp4="Scarlet_Street.mp4",
        subs=[sub("ScarletStreet", "Scarlet_Street.asr.srt", "en", auto)],
    )
    film(
        "the-red-house",
        "The Red House",
        1947,
        6005,
        ["Mystery", "Thriller"],
        "English",
        "United States",
        "Delmer Daves",
        ["Edward G. Robinson", "Lon McCallister", "Judith Anderson", "Allene Roberts"],
        "movie",
        "13+",
        "Delmer Daves's 1947 mystery with Edward G. Robinson, about a farm and a house in the woods that a teenager is told to avoid. The archive item is marked public domain.",
        ["international-movies", "classic-cinema", "mystery-and-thriller"],
        "TheRedHouse_123",
        "public-domain",
        "http://creativecommons.org/licenses/publicdomain/",
        "2026-11-08",
        mp4="TheRedHousePresentedByMoviePowder.mp4",
    )
    film(
        "kansas-city-confidential",
        "Kansas City Confidential",
        1952,
        5941,
        ["Thriller", "Crime"],
        "English",
        "United States",
        "Phil Karlson",
        ["John Payne", "Coleen Gray", "Preston Foster"],
        "movie",
        "13+",
        "Phil Karlson's 1952 crime film. An armoured-car robbery leaves a delivery driver as the suspect. The archive item is marked public domain.",
        ["international-movies", "classic-cinema", "mystery-and-thriller", "action-and-adventure"],
        "kansascityconfidencial",
        "public-domain",
        "http://creativecommons.org/licenses/publicdomain/",
        "2026-11-09",
        mp4="kansascityconfidencial.mp4",
        subs=[sub("kansascityconfidencial", "kansascityconfidencial.asr.srt", "en", auto)],
    )
    film(
        "suddenly",
        "Suddenly",
        1954,
        4547,
        ["Thriller", "Crime"],
        "English",
        "United States",
        "Lewis Allen",
        ["Frank Sinatra", "Sterling Hayden", "James Gleason"],
        "movie",
        "16+",
        "Lewis Allen's 1954 thriller. Gunmen take over a house above a railway stop. The archive item carries a Public Domain Mark.",
        ["international-movies", "classic-cinema", "mystery-and-thriller"],
        "Suddenly_1954",
        "public-domain-mark",
        "https://creativecommons.org/publicdomain/mark/1.0/",
        "2026-11-10",
        mp4="Suddenly_1954.mp4",
    )
    film(
        "house-on-haunted-hill",
        "House on Haunted Hill",
        1959,
        4483,
        ["Horror", "Mystery"],
        "English",
        "United States",
        "William Castle",
        ["Vincent Price", "Carol Ohmart"],
        "movie",
        "13+",
        "William Castle's 1959 horror film. Vincent Price offers guests money to spend the night in a house. The archive item is marked public domain.",
        ["international-movies", "classic-cinema", "mystery-and-thriller"],
        "The_House_On_Haunted_Hill",
        "public-domain",
        "http://creativecommons.org/licenses/publicdomain/",
        "2026-11-04",
        mp4="The_House_On_Haunted_Hill.mp4",
        subs=[sub("The_House_On_Haunted_Hill", "The_House_On_Haunted_Hill.asr.srt", "en", auto)],
    )
    film(
        "plan-9-from-outer-space",
        "Plan 9 from Outer Space",
        1959,
        4700,
        ["Science Fiction", "Comedy", "Horror"],
        "English",
        "United States",
        "Ed Wood",
        ["Bela Lugosi", "Maila Nurmi", "Tor Johnson", "Gregory Walcott"],
        "movie",
        "13+",
        "Ed Wood's 1959 science-fiction film about grave-robbing aliens. The archive item is marked CC0.",
        ["international-movies", "classic-cinema", "comedy", "independent-films", "mystery-and-thriller"],
        "plan-9-from-outer-space",
        "cc0",
        "https://creativecommons.org/publicdomain/zero/1.0/",
        "2026-11-16",
        mp4="plan-9-from-outer-space.mp4",
        subs=[sub("plan-9-from-outer-space", "plan-9-from-outer-space.asr.srt", "en", auto)],
        featured=True,
    )
    film(
        "the-little-shop-of-horrors",
        "The Little Shop of Horrors",
        1960,
        4353,
        ["Comedy", "Horror"],
        "English",
        "United States",
        "Roger Corman",
        ["Jonathan Haze", "Jackie Joseph", "Mel Welles"],
        "movie",
        "13+",
        "Roger Corman's 1960 comic horror film about a florist's assistant and a plant that feeds on blood. This is the 1960 film, not the later musical. The archive item carries a Public Domain Mark.",
        ["international-movies", "classic-cinema", "comedy", "independent-films", "mystery-and-thriller"],
        "TheLittleShopOfHorrors1960",
        "public-domain-mark",
        "https://creativecommons.org/publicdomain/mark/1.0/",
        "2026-11-11",
        mp4="The-Little-Shop-of-Horrors.mp4",
        subs=[sub("TheLittleShopOfHorrors1960", "The-Little-Shop-of-Horrors.asr.srt", "en", auto)],
    )
    film(
        "carnival-of-souls",
        "Carnival of Souls",
        1962,
        4980,
        ["Horror", "Mystery"],
        "English",
        "United States",
        "Herk Harvey",
        ["Candace Hilligoss"],
        "movie",
        "13+",
        "Herk Harvey's 1962 independent horror film. After a car accident, a woman is drawn to an abandoned pavilion. The archive item is marked public domain.",
        ["international-movies", "classic-cinema", "mystery-and-thriller", "independent-films"],
        "CarnivalOfSouls_ipod",
        "public-domain",
        "http://creativecommons.org/licenses/publicdomain/",
        "2026-11-12",
        mp4="CarnivalOfSouls.mp4",
        subs=[sub("CarnivalOfSouls_ipod", "CarnivalOfSouls.asr.srt", "en", auto)],
    )
    film(
        "the-last-man-on-earth",
        "The Last Man on Earth",
        1964,
        5204,
        ["Science Fiction", "Horror"],
        "English",
        "United States",
        "Ubaldo Ragona, Sidney Salkow",
        ["Vincent Price"],
        "movie",
        "16+",
        "A 1964 science-fiction horror film with Vincent Price as a scientist who believes he is the last living man after a plague. The archive item carries a Public Domain Mark.",
        ["international-movies", "classic-cinema", "mystery-and-thriller"],
        "TheLastManOnEarth1964_201808",
        "public-domain-mark",
        "https://creativecommons.org/publicdomain/mark/1.0/",
        "2026-11-14",
        mp4="The Last Man on Earth (1964).mp4",
    )
    film(
        "night-of-the-living-dead",
        "Night of the Living Dead",
        1968,
        5796,
        ["Horror"],
        "English",
        "United States",
        "George A. Romero",
        ["Duane Jones", "Judith O'Dea", "Karl Hardman"],
        "movie",
        "16+",
        "George A. Romero's 1968 horror film. Strangers shelter in a farmhouse while the dead walk. The film is in the public domain because of a missing copyright notice. The archive item carries a Public Domain Mark.",
        ["international-movies", "classic-cinema", "mystery-and-thriller", "independent-films"],
        "night-of-the-living-dead_1968",
        "public-domain-mark",
        "https://creativecommons.org/publicdomain/mark/1.0/",
        "2026-11-13",
        mp4="Night of the Living Dead - (1968).mp4",
        featured=True,
    )
    film(
        "the-eagle-has-landed",
        "The Eagle Has Landed: The Flight of Apollo 11",
        1969,
        1706,
        ["Documentary", "Science"],
        "English",
        "United States",
        "NASA",
        [],
        "documentary",
        "All",
        "A 1969 NASA film about the flight of Apollo 11, held by the U.S. National Archives as item 45017 and marked CC0 on the Internet Archive. About 28 minutes.",
        ["documentaries", "educational-movies", "science-and-technology", "international-movies", "kids-movies", "kids-science", "kids-learning", "kids-family", "family-entertainment"],
        "gov.archives.arc.45017",
        "cc0",
        "https://creativecommons.org/publicdomain/zero/1.0/",
        "2026-11-17",
        mp4="gov.archives.arc.45017_512kb.mp4",
        quality_note=small,
        rights_holder="U.S. National Archives / NASA",
        holder_slug="national-archives",
        review={
            "status": "approved",
            "suitability": "9-12",
            "notes": "Manual review on 2026-11-23. Historical NASA documentary of Apollo 11, about 28 minutes. No graphic imagery. Approved for ages 9–12 and for family viewing. Not aimed at preschool.",
            "reviewedAt": "2026-11-23",
        },
        featured=True,
    )
    film(
        "big-buck-bunny",
        "Big Buck Bunny",
        2008,
        596,
        ["Animation", "Comedy", "Short", "Cartoon"],
        "No dialogue",
        "Netherlands",
        "Sacha Goedegebure",
        [],
        "short",
        "6+",
        "A 2008 open movie from the Blender Foundation, about 10 minutes. A large rabbit deals with three bullying rodents. Licensed CC BY 3.0. Playback is the Internet Archive player for the Foundation's own release on item BigBuckBunny.",
        ["international-movies", "animated-movies", "cartoons", "short-films", "comedy", "family-entertainment", "kids-movies", "kids-animated-movies", "kids-adventure-cartoons", "kids-family"],
        "BigBuckBunny",
        "cc-by-3.0",
        "https://creativecommons.org/licenses/by/3.0/",
        "2026-11-18",
        note="The Foundation's direct download host refused this network with HTTP 403, so playback uses the Internet Archive copy of the same CC BY 3.0 release. Credit the Blender Foundation, www.bigbuckbunny.org. Rights-holder page: https://peach.blender.org/about/",
        rights_holder="Blender Foundation",
        holder_slug="blender-foundation",
        review={
            "status": "approved",
            "suitability": "6-8",
            "notes": "Manual review on 2026-11-23. Cartoon slapstick of about 10 minutes. A butterfly is harmed and the rabbit retaliates. No dialogue. Approved for ages 6 and up and for family viewing. Not published for preschool.",
            "reviewedAt": "2026-11-23",
        },
        featured=True,
    )
    film(
        "caminandes-llama-drama",
        "Caminandes: Llama Drama",
        2013,
        90,
        ["Animation", "Comedy", "Short", "Cartoon"],
        "No dialogue",
        "Netherlands",
        "Pablo Vazquez",
        [],
        "short",
        "All",
        "A 2013 Blender open movie, about 90 seconds, of a llama in Patagonia trying to reach a tuft of grass. No dialogue. The archive item is licensed CC BY 3.0.",
        ["international-movies", "animated-movies", "cartoons", "short-films", "comedy", "family-entertainment", "kids-movies", "kids-preschool", "kids-animated-movies", "kids-family"],
        "Caminandes1LlamaDrama",
        "cc-by-3.0",
        "https://creativecommons.org/licenses/by/3.0/",
        "2026-11-19",
        mp4="01_llama_drama_1080p.mp4",
        rights_holder="Blender Foundation",
        holder_slug="blender-foundation",
        review={
            "status": "approved",
            "suitability": "preschool",
            "notes": "Manual review on 2026-11-23. About 90 seconds, no dialogue, a llama and a small meal. No scary imagery. Approved for preschool and family viewing.",
            "reviewedAt": "2026-11-23",
        },
        featured=True,
    )
    film(
        "caminandes-gran-dillama",
        "Caminandes: Gran Dillama",
        2013,
        146,
        ["Animation", "Comedy", "Short", "Cartoon"],
        "No dialogue",
        "Netherlands",
        "Pablo Vazquez",
        [],
        "short",
        "All",
        "A 2013 Blender open movie, about two and a half minutes, following the llama Koro in Patagonia. No dialogue. The archive item is licensed CC BY 3.0.",
        ["international-movies", "animated-movies", "cartoons", "short-films", "comedy", "family-entertainment", "kids-movies", "kids-preschool", "kids-animated-movies", "kids-family"],
        "Caminandes2GranDillama",
        "cc-by-3.0",
        "https://creativecommons.org/licenses/by/3.0/",
        "2026-11-20",
        mp4="02_gran_dillama_1080p.mp4",
        rights_holder="Blender Foundation",
        holder_slug="blender-foundation",
        review={
            "status": "approved",
            "suitability": "preschool",
            "notes": "Manual review on 2026-11-23. Short animal comedy, no dialogue. Approved for preschool and family viewing.",
            "reviewedAt": "2026-11-23",
        },
    )
    film(
        "sintel",
        "Sintel",
        2010,
        888,
        ["Animation", "Fantasy", "Short", "Drama"],
        "English",
        "Netherlands",
        "Colin Levy",
        [],
        "short",
        "13+",
        "A 2010 Blender Foundation open movie, about 15 minutes, about a girl searching for a dragon. It includes injury and death. Licensed CC BY 3.0. Not published in Kids Cinema.",
        ["international-movies", "animated-movies", "short-films", "drama"],
        "Sintel",
        "cc-by-3.0",
        "https://creativecommons.org/licenses/by/3.0/",
        "2026-11-22",
        mp4="sintel-2048-stereo.mp4",
        rights_holder="Blender Foundation",
        holder_slug="blender-foundation",
        note="Rights-holder page: https://durian.blender.org/sharing/",
        review={
            "status": "rejected",
            "suitability": "not-for-kids",
            "notes": "Manual review on 2026-11-23. Fantasy violence and the death of a companion. Rejected for every Kids Cinema age group.",
            "reviewedAt": "2026-11-23",
        },
    )
    film(
        "elephants-dream",
        "Elephants Dream",
        2006,
        654,
        ["Animation", "Fantasy", "Short"],
        "English",
        "Netherlands",
        "Bassam Kurdali",
        ["Tygo Gernandt", "Cas Jansen"],
        "short",
        "13+",
        "A 2006 Blender open movie, about 11 minutes, of two people inside a strange machine. Licensed CC BY 3.0. Not published in Kids Cinema.",
        ["international-movies", "animated-movies", "short-films"],
        "ElephantsDream",
        "cc-by-3.0",
        "https://creativecommons.org/licenses/by/3.0/",
        "2026-11-21",
        mp4="ed_1024.mp4",
        rights_holder="Blender Foundation",
        holder_slug="blender-foundation",
        note="The archive item names the CC BY 3.0 US port. The deed used here is the international CC BY 3.0 licence. Project page: https://orange.blender.org/",
        review={
            "status": "rejected",
            "suitability": "not-for-kids",
            "notes": "Manual review on 2026-11-23. Surreal imagery that is not made for children. Rejected for every Kids Cinema age group.",
            "reviewedAt": "2026-11-23",
        },
    )
    film(
        "cosmos-laundromat",
        "Cosmos Laundromat: First Cycle",
        2015,
        731,
        ["Animation", "Comedy", "Short"],
        "English",
        "Netherlands",
        "Mathieu Auvray",
        [],
        "short",
        "13+",
        "A 2015 Blender open movie, about 12 minutes. A sheep on an island meets a salesman. The story deals with despair. Licensed CC BY 4.0. Not published in Kids Cinema.",
        ["international-movies", "animated-movies", "short-films", "comedy"],
        "CosmosLaundromatFirstCycle",
        "cc-by-4.0",
        "https://creativecommons.org/licenses/by/4.0/",
        "2026-11-23",
        mp4="Cosmos Laundromat - First Cycle (1080p).mp4",
        subs=[
            sub("CosmosLaundromatFirstCycle", "CosmosLaundromat-FirstCycle1080p.en.srt", "en", "English"),
            sub("CosmosLaundromatFirstCycle", "CosmosLaundromat-FirstCycle1080p.es.srt", "es", "Spanish"),
            sub("CosmosLaundromatFirstCycle", "CosmosLaundromat-FirstCycle1080p.fr.srt", "fr", "French"),
        ],
        rights_holder="Blender Foundation",
        holder_slug="blender-foundation",
        review={
            "status": "rejected",
            "suitability": "not-for-kids",
            "notes": "Manual review on 2026-11-23. The story deals with despair and death. Rejected for every Kids Cinema age group.",
            "reviewedAt": "2026-11-23",
        },
    )

    add_verified_additions(rows, ROOT)

    known = {c[0] for c in CATEGORIES}
    for movie in rows:
        missing = [c for c in movie["categories"] if c not in known]
        if missing:
            raise SystemExit(f"{movie['slug']} unknown categories {missing}")
        if not movie["sources"]:
            raise SystemExit(f"{movie['slug']} has no playback")
        for source in movie["sources"]:
            if not source["licenceEvidenceUrl"].startswith("http"):
                raise SystemExit(f"{movie['slug']} missing licence")
            if not source["url"].startswith(("https://archive.org/", "https://www.youtube-nocookie.com/embed/")):
                raise SystemExit(f"{movie['slug']} playback is not an Internet Archive or official YouTube embed URL")
            if source["rightsVerified"] is not True:
                raise SystemExit(f"{movie['slug']} unverified")
        kids_cats = [c for c in movie["categories"] if c.startswith("kids-") or c in {"kids-movies", "family-entertainment", "cartoons"}]
        # cartoons includes non-kids? We only put kids titles in cartoons. family-entertainment includes only approved.
        if any(c.startswith("kids-") or c == "kids-movies" or c == "family-entertainment" for c in movie["categories"]):
            if not movie["review"] or movie["review"]["status"] != "approved":
                raise SystemExit(f"{movie['slug']} is in a kids or family category without approval")

    catalog = {
        "demo": True,
        "verifiedOn": "2026-11-23",
        "name": "SOSPANA CINEMA",
        "tagline": "Free Entertainment. Everywhere.",
        "heroSlug": "sherlock-jr",
        "trending": [
            "sherlock-jr",
            "the-general",
            "metropolis",
            "nosferatu",
            "his-girl-friday",
            "big-buck-bunny",
            "a-trip-to-the-moon",
            "plan-9-from-outer-space",
        ],
        "popular": [
            "charade",
            "night-of-the-living-dead",
            "the-cabinet-of-dr-caligari",
            "safety-last",
            "steamboat-bill-jr",
            "sintel",
            "the-phantom-of-the-opera",
            "detour",
        ],
        "categories": [
            {
                "id": uid("category:" + slug),
                "slug": slug,
                "name": name,
                "description": description,
            }
            for slug, name, description in CATEGORIES
        ],
        "sources": [
            {
                "id": uid("source:" + source["slug"]),
                "slug": source["slug"],
                **{k: v for k, v in source.items() if k != "slug"},
            }
            for source in SOURCES
        ],
        "movies": [],
    }
    for movie in rows:
        mid = uid("movie:" + movie["slug"])
        streams = []
        for index, source in enumerate(movie["sources"]):
            streams.append(
                {
                    "id": uid(f"stream:{movie['slug']}:{index}:{source['playbackType']}"),
                    "movieId": mid,
                    "providerId": uid("source:" + source["providerSlug"]),
                    "providerSlug": source["providerSlug"],
                    "playbackType": source["playbackType"],
                    "url": source["url"],
                    "licenceType": source["licenceType"],
                    "licenceEvidenceUrl": source["licenceEvidenceUrl"],
                    "sourceRecordUrl": source["sourceRecordUrl"],
                    "licenceTerritories": source["licenceTerritories"],
                    "licenceExpiry": None,
                    "rightsVerified": True,
                    "playbackStatus": "available",
                    "lastVerifiedAt": source["lastVerifiedAt"],
                    "rightsHolder": source["rightsHolder"],
                    "rightsHolderSource": source["rightsHolderSource"],
                    "subtitles": source["subtitles"],
                    "qualityNote": source["qualityNote"],
                }
            )
        review = None
        if movie["review"]:
            review = {
                "id": uid("review:" + movie["slug"]),
                "movieId": mid,
                "reviewStatus": movie["review"]["status"],
                "ageSuitability": movie["review"]["suitability"],
                "reviewNotes": movie["review"]["notes"],
                "reviewedAt": movie["review"]["reviewedAt"],
            }
        catalog["movies"].append(
            {
                "id": mid,
                "slug": movie["slug"],
                "title": movie["title"],
                "description": movie["description"],
                "releaseYear": movie["releaseYear"],
                "runtimeSeconds": movie["runtimeSeconds"],
                "genres": movie["genres"],
                "language": movie["language"],
                "country": movie["country"],
                "director": movie["director"],
                "cast": movie["cast"],
                "contentType": movie["contentType"],
                "ageRating": movie["ageRating"],
                "posterUrl": movie["posterUrl"],
                "backdropUrl": movie["backdropUrl"],
                "trailerUrl": movie["trailerUrl"],
                "categorySlugs": movie["categories"],
                "featured": movie["featured"],
                "published": True,
                "createdAt": movie["createdAt"],
                "updatedAt": movie["updatedAt"],
                "note": movie["note"],
                "sources": streams,
                "review": review,
            }
        )
    slugs = {m["slug"] for m in catalog["movies"]}
    for key in ("heroSlug",):
        if catalog[key] not in slugs:
            raise SystemExit("bad hero")
    for key in ("trending", "popular"):
        for slug in catalog[key]:
            if slug not in slugs:
                raise SystemExit(f"bad {key} {slug}")
    return catalog


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def sql_array(values: list[str]) -> str:
    if not values:
        return "ARRAY[]::text[]"
    return "ARRAY[" + ", ".join(sql_literal(v) for v in values) + "]"


def write_sql(catalog: dict, path: Path) -> None:
    lines = [
        "-- Demonstration seed for Sospana Cinema.",
        "-- Real public-domain and Creative Commons titles only. Verified 2026-11-23.",
        "-- Safe to re-run.",
        "begin;",
    ]
    for source in catalog["sources"]:
        lines.append(
            "insert into public.content_sources (id, provider_name, website_url, provider_type, api_status, terms_reference) values ("
            + ", ".join(
                [
                    sql_literal(source["id"]) + "::uuid",
                    sql_literal(source["providerName"]),
                    sql_literal(source["websiteUrl"]),
                    sql_literal(source["providerType"]),
                    sql_literal(source["apiStatus"]),
                    sql_literal(source["termsReference"]),
                ]
            )
            + ") on conflict (id) do nothing;"
        )
    for category in catalog["categories"]:
        lines.append(
            "insert into public.categories (id, name, slug, description) values ("
            + ", ".join(
                [
                    sql_literal(category["id"]) + "::uuid",
                    sql_literal(category["name"]),
                    sql_literal(category["slug"]),
                    sql_literal(category["description"]),
                ]
            )
            + ") on conflict (slug) do nothing;"
        )
    for movie in catalog["movies"]:
        lines.append(
            "insert into public.movies (id, title, slug, description, release_year, runtime_seconds, genres, language, country, director, cast_members, content_type, age_rating, poster_url, backdrop_url, trailer_url, published, featured, catalogue_note, created_at, updated_at) values ("
            + ", ".join(
                [
                    sql_literal(movie["id"]) + "::uuid",
                    sql_literal(movie["title"]),
                    sql_literal(movie["slug"]),
                    sql_literal(movie["description"]),
                    str(movie["releaseYear"]),
                    str(movie["runtimeSeconds"]),
                    sql_array(movie["genres"]),
                    sql_literal(movie["language"]),
                    sql_literal(movie["country"]),
                    sql_literal(movie["director"]),
                    sql_array(movie["cast"]),
                    sql_literal(movie["contentType"]),
                    sql_literal(movie["ageRating"]),
                    sql_literal(movie["posterUrl"]),
                    sql_literal(movie["backdropUrl"]),
                    "null" if not movie["trailerUrl"] else sql_literal(movie["trailerUrl"]),
                    "true",
                    "true" if movie["featured"] else "false",
                    "null" if not movie["note"] else sql_literal(movie["note"]),
                    sql_literal(movie["createdAt"]) + "::timestamptz",
                    sql_literal(movie["updatedAt"]) + "::timestamptz",
                ]
            )
            + ") on conflict (slug) do nothing;"
        )
        for slug in movie["categorySlugs"]:
            lines.append(
                "insert into public.movie_categories (movie_id, category_id) select "
                + sql_literal(movie["id"])
                + "::uuid, id from public.categories where slug = "
                + sql_literal(slug)
                + " on conflict do nothing;"
            )
        for source in movie["sources"]:
            lines.append(
                "insert into public.streaming_sources (id, movie_id, provider_id, playback_type, authorized_embed_url, licence_type, licence_evidence_url, source_record_url, licence_territories, licence_expiry, rights_verified, playback_status, last_verified_at, rights_holder, subtitles, quality_note) values ("
                + ", ".join(
                    [
                        sql_literal(source["id"]) + "::uuid",
                        sql_literal(movie["id"]) + "::uuid",
                        sql_literal(source["providerId"]) + "::uuid",
                        sql_literal(source["playbackType"]),
                        sql_literal(source["url"]),
                        sql_literal(source["licenceType"]),
                        sql_literal(source["licenceEvidenceUrl"]),
                        sql_literal(source["sourceRecordUrl"]),
                        sql_array(source["licenceTerritories"]),
                        "null",
                        "true",
                        sql_literal(source["playbackStatus"]),
                        sql_literal(source["lastVerifiedAt"]) + "::timestamptz",
                        sql_literal(source["rightsHolder"]),
                        sql_literal(json.dumps(source["subtitles"])) + "::jsonb",
                        sql_literal(source["qualityNote"]),
                    ]
                )
                + ") on conflict (id) do nothing;"
            )
        if movie["review"]:
            review = movie["review"]
            lines.append(
                "insert into public.content_reviews (id, movie_id, review_status, age_suitability, review_notes, reviewed_at) values ("
                + ", ".join(
                    [
                        sql_literal(review["id"]) + "::uuid",
                        sql_literal(movie["id"]) + "::uuid",
                        sql_literal(review["reviewStatus"]),
                        sql_literal(review["ageSuitability"]),
                        sql_literal(review["reviewNotes"]),
                        sql_literal(review["reviewedAt"]) + "::date",
                    ]
                )
                + ") on conflict (id) do nothing;"
            )
    lines.append("commit;")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    catalog = build()
    data = ROOT / "data"
    data.mkdir(parents=True, exist_ok=True)
    (data / "catalog.json").write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    supabase = ROOT / "supabase"
    supabase.mkdir(parents=True, exist_ok=True)
    write_sql(catalog, supabase / "seed.sql")
    print(f"movies {len(catalog['movies'])}")
    print(f"categories {len(catalog['categories'])}")


if __name__ == "__main__":
    main()
