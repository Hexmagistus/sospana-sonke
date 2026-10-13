"""Forgiving public search: synonyms and a one-letter typo on known words.

The original phrase is always kept. A single known word such as "learnerships"
also matches the singular and the stored opportunity type. A mixed phrase such
as "nurse learnership" stays a title search, so it does not return every
learnership.
"""
from __future__ import annotations

_GROUPS: dict[str, tuple[str, ...]] = {
    "learnership": ("learnership", "learnerships"),
    "internship": ("internship", "internships", "intern"),
    "bursary": ("bursary", "bursaries", "scholarship", "scholarships"),
    "graduate_programme": (
        "graduate programme",
        "graduate program",
        "graduate programmes",
        "graduate programs",
    ),
}

# Words a person might type, mapped to a group. Includes the common misspellings
# we have actually seen people use for these five programme words.
_WORD: dict[str, str] = {}
for _group, _words in _GROUPS.items():
    for _word in _words:
        _WORD[_word] = _group
_WORD.update({
    "lernership": "learnership",
    "lernerships": "learnership",
    "learneship": "learnership",
    "learneships": "learnership",
    "intership": "internship",
    "internships": "internship",
    "bursry": "bursary",
    "bursaries": "bursary",
})


def _distance(left: str, right: str) -> int:
    if abs(len(left) - len(right)) > 1:
        return 2
    prev = list(range(len(right) + 1))
    for i, a in enumerate(left, start=1):
        cur = [i]
        for j, b in enumerate(right, start=1):
            cur.append(min(
                prev[j] + 1,
                cur[j - 1] + 1,
                prev[j - 1] + (a != b),
            ))
        prev = cur
    return prev[-1]


def _group_for_token(token: str) -> str | None:
    if token in _WORD:
        return _WORD[token]
    if len(token) < 6:
        return None
    for known, group in _WORD.items():
        if " " in known:
            continue
        if _distance(token, known) == 1:
            return group
    return None


def expand_title_terms(query: str) -> list[str]:
    """Title phrases to match. At most eight, original first."""
    cleaned = " ".join(query.strip().split())[:80]
    if not cleaned:
        return []
    lowered = cleaned.lower()
    found: list[str] = [cleaned]
    if lowered in _WORD:
        for phrase in _GROUPS[_WORD[lowered]]:
            if phrase not in found:
                found.append(phrase)
        return found[:8]
    words = lowered.split()
    for index, word in enumerate(words):
        group = _group_for_token(word)
        if not group:
            continue
        for phrase in _GROUPS[group]:
            if " " in phrase:
                continue
            swapped = words[:]
            swapped[index] = phrase
            text = " ".join(swapped)
            if text not in found:
                found.append(text)
    return found[:8]


def opportunity_types_for(query: str) -> list[str]:
    """Type filter when the whole query is a programme word, not a mixed phrase."""
    cleaned = " ".join(query.strip().lower().split())
    if not cleaned:
        return []
    group = _WORD.get(cleaned)
    if group is None and " " not in cleaned:
        group = _group_for_token(cleaned)
    if group in _GROUPS:
        return [group]
    return []
