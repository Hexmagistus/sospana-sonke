"""AI provider factory. Chooses the provider from config, with heuristic default."""
from __future__ import annotations

from app.ai.base import AIProvider, StructuredCV  # noqa: F401
from app.ai.heuristic import HeuristicProvider
from app.core.config import settings


def get_ai_provider() -> AIProvider:
    provider = settings.AI_PROVIDER
    if provider == "claude":
        try:
            from app.ai.claude import ClaudeProvider
            return ClaudeProvider()
        except Exception:
            # Graceful fallback (blueprint section 35): never break on AI config issues.
            return HeuristicProvider()
    return HeuristicProvider()


def structure_cv_with_fallback(text: str) -> tuple[StructuredCV, str]:
    """Structure a CV, returning (result, model_name). Falls back to heuristic on error."""
    provider = get_ai_provider()
    try:
        return provider.structure_cv(text), provider.name
    except Exception:
        fallback = HeuristicProvider()
        return fallback.structure_cv(text), fallback.name
