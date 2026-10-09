"""The URL tester and the page hasher share the scraper's redirect check."""
import httpx

from app.models.company import Company
from app.scraper.ssrf import SsrfBlocked
from app.scraper.safe_fetch import checked_get, follow_redirects
from app.services.link_check_service import check_company_content
from app.services.url_tester import test_url_sync as check_url_sync


class _Resp:
    def __init__(self, status_code, location=None, text="ok", url="https://jobs.example/careers"):
        self.status_code = status_code
        self.headers = {"location": location} if location else {}
        self.text = text
        self.url = url


class _Client:
    def __init__(self, responses):
        self.responses = list(responses)
        self.urls = []

    def get(self, url, **kwargs):
        self.urls.append(url)
        return self.responses.pop(0)


def test_redirect_to_loopback_is_not_fetched():
    client = _Client([
        _Resp(302, location="http://127.0.0.1/latest/meta-data/"),
        _Resp(200, text="secret"),
    ])
    try:
        follow_redirects(lambda url: client.get(url, follow_redirects=False), "https://jobs.example/careers")
    except SsrfBlocked as exc:
        assert exc.verdict == "private_ip"
    else:
        raise AssertionError("loopback redirect was followed")
    assert client.urls == ["https://jobs.example/careers"]


def test_redirect_to_metadata_address_is_not_fetched():
    client = _Client([
        _Resp(301, location="http://169.254.169.254/latest/meta-data/"),
    ])
    try:
        checked_get(client, "https://jobs.example/careers")
    except SsrfBlocked as exc:
        assert exc.verdict == "private_ip"
    else:
        raise AssertionError("metadata redirect was followed")
    assert client.urls == ["https://jobs.example/careers"]


def test_public_redirect_is_followed():
    client = _Client([
        _Resp(302, location="https://boards.example/jobs", url="https://jobs.example/careers"),
        _Resp(200, text="<title>Careers</title> Lecturer", url="https://boards.example/jobs"),
    ])
    resp = checked_get(client, "https://jobs.example/careers")
    assert resp.status_code == 200
    assert "Lecturer" in resp.text
    assert client.urls == ["https://jobs.example/careers", "https://boards.example/jobs"]


def test_url_tester_refuses_a_private_redirect_and_keeps_the_body():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        if request.url.host == "jobs.example":
            return httpx.Response(302, headers={"location": "http://127.0.0.1/secret"}, request=request)
        return httpx.Response(200, text="secret", request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        blocked = check_url_sync("https://jobs.example/careers", client=client)
        assert not any("127.0.0.1" in url for url in seen)
        seen.clear()

        def safe(request: httpx.Request) -> httpx.Response:
            seen.append(str(request.url))
            if request.url.host == "jobs.example":
                return httpx.Response(
                    302, headers={"location": "https://boards.example/careers"}, request=request,
                )
            return httpx.Response(200, text="<title>Job vacancies</title>", request=request)

    with httpx.Client(transport=httpx.MockTransport(safe)) as client:
        followed = check_url_sync("https://jobs.example/careers", client=client)

    assert blocked.ok is False
    assert blocked.error and "private_ip" in blocked.error
    assert followed.ok is True
    assert followed.final_url == "https://boards.example/careers"
    assert "127.0.0.1" not in " ".join(seen)


def test_page_hasher_does_not_follow_a_metadata_redirect(db):
    company = Company(
        company_name="Redirect Uni", source_type="UNI", country="Zambia",
        careers_url="https://jobs.example/careers", active=True,
    )
    db.add(company)
    db.commit()

    class Recording:
        def __init__(self):
            self.urls = []

        def get(self, url, **kwargs):
            self.urls.append(url)
            return _Resp(302, location="http://169.254.169.254/latest/meta-data/", text="secret")

    client = Recording()
    changed = check_company_content(company, client=client)
    assert changed is False
    assert company.content_hash is None
    assert client.urls == ["https://jobs.example/careers"]
