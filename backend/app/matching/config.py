"""Match configuration: weights, thresholds, and bands (blueprint section 8).

All values are configurable by the administrator (stored in system_settings). The
defaults below match the blueprint's suggested starting weights. Weights are
normalised at scoring time, so they need not sum to exactly 100.
"""
from __future__ import annotations

from dataclasses import dataclass, field

DEFAULT_WEIGHTS = {
    "qualification": 25,
    "experience": 25,
    "skills": 20,
    "title": 10,
    "industry": 5,
    "location": 5,
    "certification": 5,
    "other": 5,
}

DEFAULT_BANDS = {"strong": 85, "good": 75, "possible": 65, "weak": 55}


@dataclass
class MatchConfig:
    weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))
    apply_threshold: float = 80.0
    review_threshold: float = 60.0
    bands: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_BANDS))

    @classmethod
    def from_dict(cls, data: dict | None) -> "MatchConfig":
        if not data:
            return cls()
        return cls(
            weights={**DEFAULT_WEIGHTS, **(data.get("weights") or {})},
            apply_threshold=float(data.get("apply_threshold", 80.0)),
            review_threshold=float(data.get("review_threshold", 60.0)),
            bands={**DEFAULT_BANDS, **(data.get("bands") or {})},
        )

    def to_dict(self) -> dict:
        return {"weights": self.weights, "apply_threshold": self.apply_threshold,
                "review_threshold": self.review_threshold, "bands": self.bands}

    def band_for(self, score: float) -> str:
        if score >= self.bands["strong"]:
            return "Strong"
        if score >= self.bands["good"]:
            return "Good"
        if score >= self.bands["possible"]:
            return "Possible"
        if score >= self.bands["weak"]:
            return "Weak"
        return "Reject"
