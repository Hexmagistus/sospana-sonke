"""/employers/ids and /jobs/ids are server-only once SITEMAP_API_KEY is set."""
import json
import logging

import pytest

from app.core.config import settings

PATHS = ["/api/v1/employers/ids", "/api/v1/jobs/ids"]


@pytest.mark.parametrize("path", PATHS)
def test_ids_need_the_key_when_set(client, monkeypatch, path):
    monkeypatch.setattr(settings, "SITEMAP_API_KEY", "s3cret")
    assert client.get(path).status_code == 404
    assert client.get(path, headers={"X-Internal-Key": "wrong"}).status_code == 404
    assert client.get(path, headers={"X-Internal-Key": "s3cret"}).status_code == 200


@pytest.mark.parametrize("path", PATHS)
def test_ids_refused_in_production_without_a_key(client, monkeypatch, path):
    monkeypatch.setattr(settings, "SITEMAP_API_KEY", "")
    monkeypatch.setattr(settings, "ENV", "production")
    assert client.get(path).status_code == 404


def test_bulk_calls_are_logged_with_ip_and_agent(client, caplog):
    with caplog.at_level(logging.INFO, logger="app.bulk_access"):
        client.get("/api/v1/employers?limit=5", headers={"User-Agent": "scrapy/2.11"})
    lines = [json.loads(r.getMessage()) for r in caplog.records if r.name == "app.bulk_access"]
    assert lines and lines[-1]["ua"] == "scrapy/2.11" and lines[-1]["path"] == "/api/v1/employers"
    assert "ip" in lines[-1] and "account" in lines[-1]
