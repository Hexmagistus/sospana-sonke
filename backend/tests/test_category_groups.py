"""Explorer page groups (/universities, /colleges, /hospitals, /ngos, /government)."""
import re
import uuid
from pathlib import Path

from app.services.category_groups import (
    ALIASES, CATEGORY_GROUPS, canonical_type, group_of, stored_code, stored_values_for, types_for_group,
)
from tests.conftest import register_and_login

TYPES = ["UNI", "COLLEGE", "SETA", "HOSPITAL", "NGO", "DEPT", "MUNI", "SOE", "PRIVATE", "JSE", "SPORT"]


def _seed(db_engine):
    from sqlalchemy.orm import sessionmaker
    from app.models.company import Company
    db = sessionmaker(bind=db_engine)()
    for country in ("South Africa", "Botswana", "Kenya", "Brazil"):
        for t in TYPES:
            db.add(Company(id=str(uuid.uuid4()), company_name=f"{country} {t}", country=country,
                           source_type=t, active=True))
    db.commit(); db.close()


def _h(client):
    _, tok = register_and_login(client, email="lerato@example.com")
    return {"Authorization": f"Bearer {tok['access_token']}"}


def test_mapping_is_the_agreed_one():
    assert CATEGORY_GROUPS == {
        "universities": ("UNI",),
        "colleges": ("COLLEGE", "SETA"),
        "hospitals": ("HOSPITAL",),
        "ngos": ("NGO",),
        "government": ("DEPT", "MUNI", "SOE"),
    }
    gov = types_for_group("Government")
    assert gov[:1] == ("DEPT",) and {"DEPT", "MUNI", "SOE"} <= set(gov)
    assert types_for_group("nope") is None and types_for_group(None) is None
    # No code sits in two groups, so a row is listed on one page only.
    codes = [c for types in CATEGORY_GROUPS.values() for c in types]
    assert len(codes) == len(set(codes))


def test_group_filter_lists_only_that_groups_codes(client, db_engine):
    _seed(db_engine)
    h = _h(client)
    for group, types in CATEGORY_GROUPS.items():
        rows = client.get("/api/v1/companies", params={"group": group, "limit": 1500}, headers=h).json()
        assert {r["source_type"] for r in rows} == set(types), group
        assert len(rows) == 4 * len(types), group


def test_group_and_country_combine(client, db_engine):
    _seed(db_engine)
    rows = client.get("/api/v1/companies", params={"group": "government", "country": "Kenya"}, headers=_h(client)).json()
    assert sorted(r["source_type"] for r in rows) == ["DEPT", "MUNI", "SOE"]
    assert {r["country"] for r in rows} == {"Kenya"}


def test_group_and_source_type_narrow_to_one_code(client, db_engine):
    _seed(db_engine)
    h = _h(client)
    rows = client.get("/api/v1/companies", params={"group": "colleges", "source_type": "SETA"}, headers=h).json()
    assert {r["source_type"] for r in rows} == {"SETA"} and len(rows) == 4
    # A code outside the group gives nothing rather than leaking other rows.
    assert client.get("/api/v1/companies", params={"group": "colleges", "source_type": "NGO"}, headers=h).json() == []


def test_unknown_group_is_refused(client, db_engine):
    r = client.get("/api/v1/companies", params={"group": "banks"}, headers=_h(client))
    assert r.status_code == 422
    assert "Unknown group" in r.json()["detail"]


def test_group_counts_as_a_scope_for_the_row_cap(client, db_engine, monkeypatch):
    from app.api import routes_companies
    _seed(db_engine)
    monkeypatch.setattr(routes_companies, "_UNSCOPED_USER_MAX_ROWS", 2)
    rows = client.get("/api/v1/companies", params={"group": "government", "limit": 1500}, headers=_h(client)).json()
    assert len(rows) == 12


def test_aliases_land_on_the_right_page():
    # Labels another worker may store (cut to 10 upper-case chars by the import).
    for label, code, group in [
        ("NGO", "NGO", "ngos"), ("Government", "DEPT", "government"), ("Municipality", "MUNI", "government"),
        ("SOE", "SOE", "government"), ("TVET College", "COLLEGE", "colleges"), ("SETA", "SETA", "colleges"),
        ("Parastatal", "SOE", "government"), ("npo", "NGO", "ngos"), ("  metro ", "MUNI", "government"),
    ]:
        assert canonical_type(label) == code, label
        assert group_of(label) == group, label
        assert stored_code(label) in types_for_group(group), label
    assert stored_code("TVET College") == "TVET COLLE"
    assert stored_code("Municipality") == "MUNICIPALI"
    # Codes outside the groups stay on /companies only and are left as they are.
    for other in ("JSE", "PRIVATE", "SPORT", "FED", "MUSIC", "ZSE", "", None):
        assert group_of(other) is None, other
    assert canonical_type("jse") == "JSE"
    assert stored_values_for("SOE")[0] == "SOE" and "PARASTATAL" in stored_values_for("SOE")


def test_aliases_are_unambiguous():
    canonical = {c for codes in CATEGORY_GROUPS.values() for c in codes}
    seen: dict[str, str] = {}
    for label, code in ALIASES.items():
        assert code in canonical, label
        key = stored_code(label)
        assert len(key) <= 10
        assert key not in canonical or key == code, label
        # Two labels that store the same way must mean the same code.
        assert seen.setdefault(key, code) == code, label
        # Never swallow a code that has its own meaning on /companies.
        assert key not in {"JSE", "PRIVATE", "SPORT", "FED", "MUSIC"}, label


def test_alias_rows_are_listed_and_counted_under_their_code(client, db_engine):
    from sqlalchemy.orm import sessionmaker
    from app.models.company import Company
    db = sessionmaker(bind=db_engine)()
    for name, st in [("Eskom", "SOE"), ("Old Parastatal", "PARASTATAL"), ("City of Tshwane", "MUNICIPALI"),
                     ("Some TVET", "TVET COLLE"), ("Lower NGO", "ngo"), ("Private Co", "PRIVATE")]:
        db.add(Company(id=str(uuid.uuid4()), company_name=name, country="South Africa", source_type=st, active=True))
    db.commit(); db.close()
    h = _h(client)
    names = lambda **p: sorted(r["company_name"] for r in client.get("/api/v1/companies", params=p, headers=h).json())
    assert names(group="government") == ["City of Tshwane", "Eskom", "Old Parastatal"]
    assert names(group="colleges") == ["Some TVET"]
    assert names(group="ngos") == ["Lower NGO"]
    # SOEs stay findable on /companies under the SOE category, aliases included.
    assert names(source_type="SOE") == ["Eskom", "Old Parastatal"]
    assert names(source_type="PRIVATE") == ["Private Co"]
    facets = client.get("/api/v1/companies/facets", headers=h).json()
    assert facets["type_counts"]["SOE"] == 2 and facets["type_counts"]["MUNI"] == 1
    assert facets["country_type_counts"]["South Africa"]["COLLEGE"] == 1
    assert "PARASTATAL" not in facets["type_counts"]


def test_frontend_mirror_matches():
    """frontend/src/lib/explorer/categoryGroups.ts lists the same codes per group."""
    ts = (Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib" / "explorer" / "categoryGroups.ts")
    if not ts.exists():  # backend-only checkout
        return
    src = ts.read_text(encoding="utf-8")
    src = src[src.index("export const CATEGORY_GROUPS"):src.index("export const EXPLORER_NAV")]
    blocks = re.split(r'\bgroup:\s*"', src)[1:]
    found = {b.split('"', 1)[0]: tuple(re.findall(r'\bcode:\s*"([A-Z]+)"', b)) for b in blocks}
    assert found == CATEGORY_GROUPS
    full = ts.read_text(encoding="utf-8")
    alias_block = full[full.index("export const ALIASES"):]
    alias_block = alias_block[:alias_block.index("};")]
    assert dict(re.findall(r'"([^"]+)":\s*"([A-Z]+)"', alias_block)) == ALIASES
