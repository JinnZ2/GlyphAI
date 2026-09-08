"""Typed evidence and decision objects for GlyphAI.

The existing CLI and recommendation APIs expose dictionaries. These dataclasses
provide an explicit internal model while their adapters preserve that public
shape.
"""

from dataclasses import dataclass, field
import json
import math
from typing import Any, Mapping, Optional, Tuple

SOURCE_KIND_MOCK = "mock"
SOURCE_KIND_OBSERVED = "observed"
SOURCE_KIND_DERIVED = "derived"
SOURCE_KINDS = frozenset({
    SOURCE_KIND_MOCK,
    SOURCE_KIND_OBSERVED,
    SOURCE_KIND_DERIVED,
})


def normalize_source_kind(value):
    """Return a recognized source kind, or None for absent/invalid values."""
    if isinstance(value, str) and value in SOURCE_KINDS:
        return value
    return None


def normalize_confidence(value):
    """Return a finite confidence in [0, 1], or None when it is not valid."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        return None
    return value


def _json_copy(value):
    """Validate and detach JSON-compatible domain data."""
    return json.loads(json.dumps(value, allow_nan=False))


@dataclass(frozen=True)
class Evidence:
    """A claim and its provenance.

    ``source_kind`` is optional so absent provenance stays explicitly unknown;
    it is never promoted to ``observed``. Confidence defaults to ``None``
    because GlyphAI does not yet have a calibrated confidence model.
    """

    source: str
    claim: str
    source_kind: Optional[str]
    confidence: Optional[float] = None
    supporting_data: Optional[Mapping[str, Any]] = None

    def __post_init__(self):
        if self.source_kind is not None and \
                normalize_source_kind(self.source_kind) is None:
            raise ValueError("Unknown evidence source_kind: {!r}".format(
                self.source_kind))
        if self.confidence is not None and \
                normalize_confidence(self.confidence) is None:
            raise ValueError("Evidence confidence must be between 0 and 1")

    def to_dict(self):
        """Return a detached JSON representation.

        Supporting data must itself contain JSON-compatible values.
        """
        return {
            "source": self.source,
            "claim": self.claim,
            "source_kind": self.source_kind,
            "confidence": self.confidence,
            "supporting_data": (_json_copy(dict(self.supporting_data))
                                if self.supporting_data is not None else None),
        }


@dataclass(frozen=True)
class Decision:
    """A typed recommendation with an adapter for the legacy public result."""

    action: str
    confidence: Optional[float] = None
    reasoning: Tuple[str, ...] = field(default_factory=tuple)
    warnings: Tuple[str, ...] = field(default_factory=tuple)
    evidence: Tuple[Evidence, ...] = field(default_factory=tuple)
    missing_information: Tuple[str, ...] = field(default_factory=tuple)
    alternatives: Tuple[Mapping[str, Any], ...] = field(default_factory=tuple)

    def __post_init__(self):
        if self.confidence is not None and \
                normalize_confidence(self.confidence) is None:
            raise ValueError("Decision confidence must be between 0 and 1")

    @property
    def verdict(self):
        """Alias for callers that use verdict terminology."""
        return self.action

    def to_dict(self):
        """Return the complete typed decision as JSON-serializable data."""
        return {
            "action": self.action,
            "confidence": self.confidence,
            "reasoning": list(self.reasoning),
            "warnings": list(self.warnings),
            "evidence": [item.to_dict() for item in self.evidence],
            "missing_information": list(self.missing_information),
            "alternatives": _json_copy(
                [dict(item) for item in self.alternatives]),
        }

    def to_legacy_dict(self):
        """Return the historical RecommendationEngine/CLI dictionary shape."""
        return {
            "action": self.action,
            "reasoning": list(self.reasoning),
            "alternatives": [dict(item) for item in self.alternatives],
        }

    @classmethod
    def from_recommendation(cls, recommendation, *, confidence=None,
                            warnings=None, evidence=None,
                            missing_information=None):
        """Convert an existing recommendation dictionary into a Decision."""
        return cls(
            action=recommendation["action"],
            confidence=confidence,
            reasoning=tuple(recommendation.get("reasoning") or ()),
            warnings=tuple(warnings or ()),
            evidence=tuple(evidence or ()),
            missing_information=tuple(missing_information or ()),
            alternatives=tuple(dict(item)
                               for item in recommendation.get("alternatives") or ()),
        )
