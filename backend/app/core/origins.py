"""Browser origins this API will answer with CORS headers.

Starlette's CORSMiddleware matches ``allow_origin_regex`` with ``re.match``,
which is anchored at the start and not at the end. The pattern therefore has
to end in ``\\Z`` or a lookalike host such as
``https://sospana-sonke.vercel.app.evil.com`` is treated as this project.

Production is the one Vercel alias. Preview deployments are limited to this
team's slug (``hexmagistus1``), the account that owns sospana-sonke.vercel.app.
``CORS_ORIGINS`` remains the explicit allow-list for localhost and any other
host set in the environment.
"""
import re

VERCEL_ORIGIN_REGEX = (
    r"https://(sospana-sonke\.vercel\.app|"
    r"sospana-sonke-[a-z0-9-]+-hexmagistus1\.vercel\.app)\Z"
)

_VERCEL_ORIGIN = re.compile(VERCEL_ORIGIN_REGEX)


def origin_allowed(origin: str) -> bool:
    """True when ``origin`` is this project's production or preview host."""
    return _VERCEL_ORIGIN.fullmatch(origin) is not None
