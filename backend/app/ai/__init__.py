"""AI provider factory. Chooses the provider from config, with heuristic default."""
from __future__ import annotations

import logging

from app.ai.base import AIProvider, StructuredCV  # noqa: F401
from app.ai.heuristic import HeuristicProvider
from app.core.config import settings

logger = logging.getLogger(__name__)


def get_ai_provider() -> AIProvider:
    provider = settings.AI_PROVIDER
    if provider == "claude":
        try:
            from app.ai.claude import ClaudeProvider
            return ClaudeProvider()
        except Exception:
            # Graceful fallback (blueprint section 35): never break on AI config issues.
            # But log it -- a persistent config problem (bad API key, package missing)
            # would otherwise silently downgrade every CV to the heuristic provider
            # forever with no way to notice from the outside.
            logger.warning("Claude AI provider unavailable, falling back to heuristic", exc_info=True)
            return HeuristicProvider()
    return HeuristicProvider()


def structure_cv_with_fallback(text: str) -> tuple[StructuredCV, str]:
    """Structure a CV, returning (result, model_name). Falls back to heuristic on error."""
    provider = get_ai_provider()
    try:
        return provider.structure_cv(text), provider.name
    except Exception:
        logger.warning("%s failed to structure a CV, falling back to heuristic",
                       provider.name, exc_info=True)
        fallback = HeuristicProvider()
        return fallback.structure_cv(text), fallback.name
