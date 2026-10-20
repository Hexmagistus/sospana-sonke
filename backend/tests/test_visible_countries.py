from app.services import visible_countries as vc


def test_lists_cover_sadc_brics_english(monkeypatch):
    monkeypatch.setenv("HIDE_NON_ENGLISH_COUNTRIES", "1")
    for name in ["South Africa", "Angola", "DR Congo", "Mozambique", "Brazil", "Russia", "China", "Iran",
                 "United Arab Emirates", "Indonesia", "Egypt", "Ethiopia", "Nigeria", "United Kingdom",
                 "United States", "Kenya", "Africa", "International", "", None]:
        assert vc.is_visible_country(name), name
    for name in ["Germany", "France", "Japan", "Côte d'Ivoire", "Ivory Coast", "Mexico"]:
        assert not vc.is_visible_country(name), name


def test_off_switch(monkeypatch):
    monkeypatch.setenv("HIDE_NON_ENGLISH_COUNTRIES", "0")
    assert vc.is_visible_country("Germany")


def test_clause_filters_sql(monkeypatch):
    from sqlalchemy import column
    monkeypatch.setenv("HIDE_NON_ENGLISH_COUNTRIES", "1")
    sql = str(vc.visible_country_clause(column("country")).compile(compile_kwargs={"literal_binds": True}))
    assert "'South Africa'" in sql and "'Germany'" not in sql
