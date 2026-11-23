"""Pull licence links out of a public HTML page. Does not execute scripts."""

from __future__ import annotations

from bs4 import BeautifulSoup


def licence_links(html: str) -> list[str]:
    soup = BeautifulSoup(html or "", "html.parser")
    found: list[str] = []
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        if "creativecommons.org" in href or "publicdomain" in href.lower():
            found.append(href)
    return found
