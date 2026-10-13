"""Match a work email to the directory row's own site.

The mailbox host has to share a registrable domain with the careers URL or the
official website. A free inbox never counts, even when the local part looks
official. Those claims wait for an administrator.
"""
from __future__ import annotations

from urllib.parse import urlparse

FREE_MAIL_DOMAINS = frozenset({
    "gmail.com", "googlemail.com", "yahoo.com", "yahoo.co.za", "yahoo.co.uk",
    "outlook.com", "hotmail.com", "live.com", "icloud.com", "me.com",
    "aol.com", "proton.me", "protonmail.com", "pm.me", "gmx.com", "mail.com",
    "yandex.com", "zoho.com",
})

# Second-level public suffixes we actually see on employer sites.
_PUBLIC_SUFFIXES = frozenset({
    "co.za", "org.za", "ac.za", "gov.za", "net.za", "web.za",
    "co.uk", "org.uk", "ac.uk", "gov.uk",
    "com.au", "net.au", "org.au",
    "co.nz", "org.nz", "co.ke", "or.ke", "co.ug", "co.zw", "co.bw", "co.mz",
    "com.ng", "com.br", "co.na", "com.gh",
})

ATS_HOST_SUFFIXES = (
    "greenhouse.io",
    "lever.co",
    "myworkdayjobs.com",
    "smartrecruiters.com",
    "workable.com",
    "recruitee.com",
    "teamtailor.com",
    "bamboohr.com",
    "ashbyhq.com",
    "pinpointhq.com",
    "breezy.hr",
    "icims.com",
    "oraclecloud.com",
    "successfactors.com",
    "csod.com",
    "simplify.hr",
    "ci.hr",
)


def host_of(url: str | None) -> str | None:
    if not url:
        return None
    raw = url.strip()
    if "://" not in raw:
        raw = "https://" + raw
    host = (urlparse(raw).hostname or "").lower().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    return host or None


def registrable_domain(host: str | None) -> str | None:
    if not host:
        return None
    labels = [part for part in host.lower().strip(".").split(".") if part]
    if len(labels) < 2:
        return None
    tail = ".".join(labels[-2:])
    if tail in _PUBLIC_SUFFIXES and len(labels) >= 3:
        return ".".join(labels[-3:])
    return tail


def company_domains(careers_url: str | None, official_website: str | None) -> set[str]:
    found: set[str] = set()
    for url in (careers_url, official_website):
        domain = registrable_domain(host_of(url))
        if domain and domain not in FREE_MAIL_DOMAINS:
            found.add(domain)
    return found


def email_domain(email: str) -> str | None:
    if "@" not in (email or ""):
        return None
    return registrable_domain(email.rsplit("@", 1)[1].strip().lower())


def email_matches_company(email: str, careers_url: str | None, official_website: str | None) -> bool:
    domain = email_domain(email)
    if not domain or domain in FREE_MAIL_DOMAINS:
        return False
    return domain in company_domains(careers_url, official_website)


def application_host_allowed(url: str, careers_url: str | None, official_website: str | None) -> bool:
    """The apply link stays on the employer's domain or on their applicant-system host."""
    raw = (url or "").strip()
    if not raw.lower().startswith("https://"):
        return False
    host = host_of(raw)
    if not host:
        return False
    domain = registrable_domain(host)
    if domain and domain in company_domains(careers_url, official_website):
        return True
    return any(host == suffix or host.endswith("." + suffix) for suffix in ATS_HOST_SUFFIXES)
