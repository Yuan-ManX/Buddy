from __future__ import annotations

"""Agent Cognitive Style Transfer — transfer reasoning styles, heuristics,
and problem-solving textures between domains.

The engine extracts cognitive styles from sources (domains, agents, traces,
or templates), fingerprints them as numeric vectors over a fixed set of
reasoning dimensions, and transfers those styles onto new target domains.
Styles can also be blended together to produce composite styles, and any
registered style can be applied to a problem description to produce a
suggested approach.

Core capabilities:
  - Style Extraction: build a CognitiveStyle from a free-form description
    plus an optional list of feature dicts keyed by reasoning dimension.
  - Fingerprinting: project a style's weighted features onto an ordered
    dimension vector so styles can be compared by cosine similarity.
  - Style Matching: rank registered styles by fingerprint similarity to a
    query style.
  - Style Transfer: schedule a transfer of a style onto a target domain
    under a chosen fidelity mode, then validate it against constraints.
  - Style Blending: combine several styles into a composite style using a
    weighted, dominant, mosaic, or novel blend strategy.
  - Style Application: project a style onto a problem description to
    produce a suggested approach with heuristics and a step sequence.
  - Observability: aggregate statistics expose the engine's state for
    telemetry and self-reflection.

Architecture:
    AgentCognitiveStyleTransfer (singleton)
    ├── StyleFeature       (a single dimension-weighted reasoning facet)
    ├── StyleFingerprint   (numeric vector projection of a style)
    ├── CognitiveStyle     (a named bundle of features + metadata)
    ├── StyleTransfer      (a transfer request with lifecycle + validation)
    ├── StyleBlend         (a composite style produced from several inputs)
    └── TransferStats      (aggregate counters across the engine)

The engine is intentionally dependency-free so it can run in any Buddy
runtime without extra packages. All state mutations are guarded by a
single ``threading.Lock`` and reads return fresh copies of mutable
structures so callers cannot mutate internal state by holding a reference.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Dict, List
import threading
import uuid
import time
from datetime import datetime


# =========================================================
# Enums
# =========================================================

class StyleDimension(str, Enum):
    """Reasoning dimensions along which a cognitive style can vary."""
    ANALYTICAL = "analytical"  # step-by-step decomposition and measurement
    INTUITIVE = "intuitive"    # pattern recognition and quick judgment
    DEDUCTIVE = "deductive"    # deriving conclusions from stated principles
    INDUCTIVE = "inductive"    # generalizing rules from observations
    ABDUCTIVE = "abductive"    # picking the best-fit explanation
    LATERAL = "lateral"        # reframing and side-angle approaches
    CRITICAL = "critical"      # challenging assumptions and failure modes
    CREATIVE = "creative"      # divergent generation before convergence


class TransferStatus(str, Enum):
    """Lifecycle status of a style transfer request."""
    PENDING = "pending"          # created, not yet started
    EXTRACTING = "extracting"    # reading the source style's features
    TRANSFERRING = "transferring"  # projecting the style onto the target
    VALIDATING = "validating"    # checking the transfer against constraints
    COMPLETED = "completed"      # reached a terminal state successfully
    FAILED = "failed"            # reached a terminal state with errors


class FidelityMode(str, Enum):
    """How strictly a source style must be preserved during transfer."""
    STRICT = "strict"    # preserve every dimension weight as-is
    ADAPTIVE = "adaptive"  # adjust weights to fit the target domain
    LOOSE = "loose"     # keep only the dominant dimensions


class BlendStrategy(str, Enum):
    """Strategy used to combine several styles into a composite style."""
    WEIGHTED = "weighted"  # weight each input style's contribution
    DOMINANT = "dominant"  # first style dominates, others fill gaps
    MOSAIC = "mosaic"      # each dimension taken from a single source
    NOVEL = "novel"        # average dimensions to produce a fresh profile


class SourceType(str, Enum):
    """The kind of origin a cognitive style is extracted from."""
    DOMAIN = "domain"      # a knowledge or problem domain
    AGENT = "agent"        # another agent's reasoning behavior
    TRACE = "trace"        # a recorded reasoning trace
    TEMPLATE = "template"  # a reusable style template


class ValidationStatus(str, Enum):
    """Outcome of validating a style transfer against constraints."""
    PENDING = "pending"  # not yet validated
    PASSED = "passed"    # all constraints satisfied
    FAILED = "failed"    # no constraints satisfied
    PARTIAL = "partial"  # some constraints satisfied, some not


# =========================================================
# Internal helpers
# =========================================================

# Ordered list of style dimensions used to build fingerprint vectors.
# The order is fixed so that two fingerprints can be compared position-wise.
_STYLE_DIMENSION_ORDER: List[StyleDimension] = [
    StyleDimension.ANALYTICAL,
    StyleDimension.INTUITIVE,
    StyleDimension.DEDUCTIVE,
    StyleDimension.INDUCTIVE,
    StyleDimension.ABDUCTIVE,
    StyleDimension.LATERAL,
    StyleDimension.CRITICAL,
    StyleDimension.CREATIVE,
]


def _copy_value(value: Any) -> Any:
    """Return a fresh copy of mutable containers, pass scalars through.

    Lists and dicts are shallow-copied so that callers cannot mutate the
    internal state by holding a reference to a returned value. Tuples are
    converted to lists for friendly serialization.
    """
    if isinstance(value, list):
        return list(value)
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, tuple):
        return list(value)
    return value


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a numeric value into the closed interval [low, high]."""
    if value < low:
        return low
    if value > high:
        return high
    return value


def _coerce_enum(value: Any, enum_cls: type) -> Any:
    """Coerce a value into a member of the given enum class.

    Accepts the enum directly or a case-insensitive string matching the
    member name or value. Raises ValueError when no member matches.
    """
    if isinstance(value, enum_cls):
        return value
    if isinstance(value, str):
        normalized = value.strip().upper()
        for member in enum_cls:
            if member.name == normalized or member.value == value.strip().lower():
                return member
    raise ValueError(f"Unknown {enum_cls.__name__}: {value!r}")


def _magnitude(vector: List[float]) -> float:
    """Return the Euclidean magnitude of a numeric vector."""
    total = 0.0
    for component in vector:
        total += component * component
    return total ** 0.5


def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Cosine similarity between two vectors, in [-1, 1].

    The shorter vector is padded with zeros when lengths differ. Returns
    0.0 when either vector has zero magnitude so callers do not need to
    special-case empty fingerprints.
    """
    if not vec_a or not vec_b:
        return 0.0
    if len(vec_a) != len(vec_b):
        if len(vec_a) < len(vec_b):
            vec_a = list(vec_a) + [0.0] * (len(vec_b) - len(vec_a))
        else:
            vec_b = list(vec_b) + [0.0] * (len(vec_a) - len(vec_b))
    dot = 0.0
    for a, b in zip(vec_a, vec_b):
        dot += a * b
    mag_a = _magnitude(vec_a)
    mag_b = _magnitude(vec_b)
    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0
    return dot / (mag_a * mag_b)


# =========================================================
# Data Structures
# =========================================================

@dataclass
class StyleFeature:
    """A single reasoning facet within a cognitive style.

    A feature ties a reasoning ``dimension`` to a ``weight`` in [0, 1]
    expressing how strongly the style relies on that dimension, plus a
    free-form ``description`` of how the dimension manifests.
    """
    feature_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    dimension: StyleDimension = StyleDimension.ANALYTICAL
    weight: float = 0.5
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "dimension": self.dimension.value
            if isinstance(self.dimension, StyleDimension)
            else str(self.dimension),
            "weight": self.weight,
            "description": self.description,
        }


@dataclass
class StyleFingerprint:
    """A numeric projection of a cognitive style onto the dimension vector.

    The ``vector`` has one entry per dimension in
    ``_STYLE_DIMENSION_ORDER``; each entry is the summed weight of the
    features that reference that dimension. ``dimensions_covered`` lists
    the dimension names with non-zero weight for quick inspection.
    """
    fingerprint_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    style_id: str = ""
    vector: List[float] = field(default_factory=list)
    dimensions_covered: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fingerprint_id": self.fingerprint_id,
            "style_id": self.style_id,
            "vector": list(self.vector),
            "dimensions_covered": list(self.dimensions_covered),
            "created_at": self.created_at,
        }


@dataclass
class CognitiveStyle:
    """A named bundle of reasoning features extracted from a source.

    A style carries its origin (``source_id`` and ``source_type``), a
    free-form ``description``, and a list of ``StyleFeature`` objects. A
    ``fingerprint_id`` links to the style's numeric projection once
    ``fingerprint_style`` has been called.
    """
    style_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    source_id: str = ""
    source_type: SourceType = SourceType.DOMAIN
    description: str = ""
    features: List[StyleFeature] = field(default_factory=list)
    fingerprint_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "style_id": self.style_id,
            "source_id": self.source_id,
            "source_type": self.source_type.value
            if isinstance(self.source_type, SourceType)
            else str(self.source_type),
            "description": self.description,
            "features": [
                f.to_dict() if hasattr(f, "to_dict") else dict(f)
                for f in self.features
            ],
            "fingerprint_id": self.fingerprint_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class StyleTransfer:
    """A request to transfer a style onto a target domain.

    The transfer moves through a lifecycle (pending -> extracting ->
    transferring -> validating -> completed/failed). Validation produces
    a ``validation_status`` and free-form ``validation_notes``.
    ``completed_at`` is set when the transfer reaches a terminal state.
    """
    transfer_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    source_style_id: str = ""
    target_domain: str = ""
    fidelity: FidelityMode = FidelityMode.ADAPTIVE
    description: str = ""
    status: TransferStatus = TransferStatus.PENDING
    validation_status: ValidationStatus = ValidationStatus.PENDING
    validation_notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transfer_id": self.transfer_id,
            "source_style_id": self.source_style_id,
            "target_domain": self.target_domain,
            "fidelity": self.fidelity.value
            if isinstance(self.fidelity, FidelityMode)
            else str(self.fidelity),
            "description": self.description,
            "status": self.status.value
            if isinstance(self.status, TransferStatus)
            else str(self.status),
            "validation_status": self.validation_status.value
            if isinstance(self.validation_status, ValidationStatus)
            else str(self.validation_status),
            "validation_notes": self.validation_notes,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


@dataclass
class StyleBlend:
    """A composite style produced by combining several input styles.

    The ``strategy`` determines how the input styles are combined. When
    weights are provided they align positionally with ``style_ids``. The
    ``resulting_style_id`` points to the new CognitiveStyle produced by
    the blend.
    """
    blend_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    style_ids: List[str] = field(default_factory=list)
    strategy: BlendStrategy = BlendStrategy.WEIGHTED
    weights: List[float] = field(default_factory=list)
    resulting_style_id: Optional[str] = None
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "blend_id": self.blend_id,
            "style_ids": list(self.style_ids),
            "strategy": self.strategy.value
            if isinstance(self.strategy, BlendStrategy)
            else str(self.strategy),
            "weights": list(self.weights),
            "resulting_style_id": self.resulting_style_id,
            "description": self.description,
            "created_at": self.created_at,
        }


@dataclass
class TransferStats:
    """Aggregate statistics describing the state of the engine."""
    total_styles: int = 0
    total_transfers: int = 0
    completed_transfers: int = 0
    total_blends: int = 0
    styles_by_source: Dict[str, int] = field(default_factory=dict)
    styles_by_dimension: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_styles": self.total_styles,
            "total_transfers": self.total_transfers,
            "completed_transfers": self.completed_transfers,
            "total_blends": self.total_blends,
            "styles_by_source": dict(self.styles_by_source),
            "styles_by_dimension": dict(self.styles_by_dimension),
        }


# =========================================================
# Agent Cognitive Style Transfer
# =========================================================

# Opening-step templates used when applying a style to a problem. Each
# dimension contributes a distinct first move; the remaining steps are
# filled from the ranked feature list so every active dimension gets a turn.
_DIMENSION_OPENING_STEPS: Dict[str, str] = {
    StyleDimension.ANALYTICAL.value: "Decompose the problem into measurable parts",
    StyleDimension.INTUITIVE.value: "Surface initial intuitions and gut reads",
    StyleDimension.DEDUCTIVE.value: "State assumptions and derive conclusions from them",
    StyleDimension.INDUCTIVE.value: "Gather observations and generalize patterns",
    StyleDimension.ABDUCTIVE.value: "List candidate explanations and pick the best fit",
    StyleDimension.LATERAL.value: "Reframe the problem from a side angle",
    StyleDimension.CRITICAL.value: "Challenge assumptions and identify failure modes",
    StyleDimension.CREATIVE.value: "Generate divergent options before converging",
}

# Short approach recommendations used when applying a style to a problem.
_DIMENSION_APPROACH_FRAGMENTS: Dict[str, str] = {
    StyleDimension.ANALYTICAL.value: "Break the problem down and reason over the pieces quantitatively.",
    StyleDimension.INTUITIVE.value: "Lead with pattern recognition and quick judgment, then sanity check.",
    StyleDimension.DEDUCTIVE.value: "Start from stated principles and chain them to a conclusion.",
    StyleDimension.INDUCTIVE.value: "Collect examples and infer the rule that explains them.",
    StyleDimension.ABDUCTIVE.value: "Formulate the most plausible explanation for the observations.",
    StyleDimension.LATERAL.value: "Approach the problem from an unexpected angle to unlock new options.",
    StyleDimension.CRITICAL.value: "Stress-test claims and look for what could be wrong.",
    StyleDimension.CREATIVE.value: "Diverge widely before converging on a solution.",
}


class AgentCognitiveStyleTransfer:
    """Transfer reasoning styles and problem-solving textures between domains.

    The engine maintains a registry of cognitive styles (each a bundle of
    dimension-weighted features extracted from a source), a cache of
    numeric fingerprints projected from those styles, a collection of
    transfer requests, and a collection of style blends.

    Styles can be matched against each other by cosine similarity over
    their fingerprint vectors, blended into composite styles using one of
    four strategies, and applied to a problem description to produce a
    suggested approach with an ordered step sequence.

    All state mutations are guarded by a single ``threading.Lock`` so the
    engine is safe to invoke from concurrent agent threads. Reads return
    fresh copies of mutable structures to prevent external mutation of
    internal state.

    Capabilities:
      - Extract, list, update, and delete cognitive styles.
      - Fingerprint styles into comparable numeric vectors.
      - Match styles by fingerprint similarity.
      - Create, list, and validate style transfers.
      - Blend several styles into a composite style.
      - Apply a style to a problem to get a suggested approach.
      - Report aggregate statistics over the engine's state.
    """

    # Capacity limits guarding unbounded growth.
    MAX_STYLES: int = 200
    MAX_TRANSFERS: int = 200
    MAX_BLENDS: int = 200

    def __init__(self) -> None:
        self._styles: Dict[str, CognitiveStyle] = {}
        self._fingerprints: Dict[str, StyleFingerprint] = {}
        self._transfers: Dict[str, StyleTransfer] = {}
        self._blends: Dict[str, StyleBlend] = {}
        self._lock = threading.Lock()

    # ── Style Management ───────────────────────────────────────────

    def extract_style(
        self,
        source_id: str,
        source_type: SourceType,
        description: str,
        features: Optional[List[Dict[str, Any]]] = None,
    ) -> CognitiveStyle:
        """Extract a cognitive style from a source.

        Args:
            source_id: Identifier of the source (domain id, agent id, etc.).
            source_type: The kind of source the style is extracted from.
                Accepts a SourceType or a case-insensitive string name.
            description: Free-form description of the style.
            features: Optional list of feature dicts with keys "dimension",
                "weight", and "description". When omitted, an empty feature
                list is used.

        Returns:
            The newly created CognitiveStyle registered with the engine.
        """
        with self._lock:
            if len(self._styles) >= self.MAX_STYLES:
                self._evict_oldest_style_locked()
            coerced_type = _coerce_enum(source_type, SourceType)
            parsed_features = self._parse_features_locked(features)
            style = CognitiveStyle(
                source_id=source_id,
                source_type=coerced_type,
                description=description,
                features=parsed_features,
            )
            self._styles[style.style_id] = style
            return style

    def get_style(self, style_id: str) -> Optional[CognitiveStyle]:
        """Retrieve a cognitive style by its identifier."""
        with self._lock:
            return self._styles.get(style_id)

    def list_styles(
        self,
        source_type: Optional[SourceType] = None,
        dimension: Optional[StyleDimension] = None,
    ) -> List[CognitiveStyle]:
        """List registered styles, optionally filtered.

        Args:
            source_type: Optional SourceType (or string name) to filter by.
            dimension: Optional StyleDimension (or string name); only
                styles with at least one feature in that dimension are
                returned.

        Returns:
            A list of matching CognitiveStyle objects.
        """
        with self._lock:
            coerced_type = None
            if source_type is not None:
                coerced_type = _coerce_enum(source_type, SourceType)
            coerced_dim = None
            if dimension is not None:
                coerced_dim = _coerce_enum(dimension, StyleDimension)
            result: List[CognitiveStyle] = []
            for style in self._styles.values():
                if coerced_type is not None and style.source_type != coerced_type:
                    continue
                if coerced_dim is not None:
                    has_dim = any(
                        f.dimension == coerced_dim for f in style.features
                    )
                    if not has_dim:
                        continue
                result.append(style)
            return result

    def update_style(
        self,
        style_id: str,
        description: Optional[str] = None,
        features: Optional[List[Dict[str, Any]]] = None,
    ) -> CognitiveStyle:
        """Update a cognitive style's description and/or features.

        When features are updated, any existing fingerprint is invalidated
        because the style's dimension profile has changed.

        Raises:
            KeyError: when the style_id is not registered.
        """
        with self._lock:
            style = self._styles.get(style_id)
            if style is None:
                raise KeyError(f"Style not found: {style_id}")
            if description is not None:
                style.description = description
            if features is not None:
                style.features = self._parse_features_locked(features)
                # Invalidate any existing fingerprint; the vector is stale.
                if style.fingerprint_id is not None:
                    self._fingerprints.pop(style_id, None)
                    style.fingerprint_id = None
            style.updated_at = datetime.utcnow().isoformat()
            return style

    def delete_style(self, style_id: str) -> bool:
        """Delete a cognitive style and its fingerprint.

        Returns True when a style was removed, False when the style_id
        was not registered.
        """
        with self._lock:
            if style_id not in self._styles:
                return False
            self._styles.pop(style_id, None)
            self._fingerprints.pop(style_id, None)
            return True

    # ── Fingerprinting & Matching ──────────────────────────────────

    def fingerprint_style(self, style_id: str) -> StyleFingerprint:
        """Build (or rebuild) the numeric fingerprint for a style.

        The fingerprint is a vector with one entry per dimension in
        ``_STYLE_DIMENSION_ORDER``; each entry is the summed weight of
        the style's features that reference that dimension. The
        fingerprint is cached on the engine and linked to the style via
        ``fingerprint_id``.

        Raises:
            KeyError: when the style_id is not registered.
        """
        with self._lock:
            return self._build_fingerprint_locked(style_id)

    def get_fingerprint(self, style_id: str) -> Optional[StyleFingerprint]:
        """Return the cached fingerprint for a style, or None if absent."""
        with self._lock:
            return self._fingerprints.get(style_id)

    def match_styles(
        self,
        style_id: str,
        top_k: int = 5,
    ) -> List[CognitiveStyle]:
        """Find the most similar styles to a query style by fingerprint.

        Similarity is cosine similarity over the fingerprint vectors. The
        query style itself is excluded from the results. Styles without a
        fingerprint are skipped. If the query style has no fingerprint
        yet, one is built automatically.

        Raises:
            KeyError: when the style_id is not registered.
        """
        with self._lock:
            if style_id not in self._styles:
                raise KeyError(f"Style not found: {style_id}")
            query_fp = self._fingerprints.get(style_id)
            if query_fp is None:
                query_fp = self._build_fingerprint_locked(style_id)
            scored: List[tuple] = []
            for other_id, other_fp in self._fingerprints.items():
                if other_id == style_id:
                    continue
                score = _cosine_similarity(query_fp.vector, other_fp.vector)
                scored.append((score, other_id))
            # Sort by descending similarity; ties break by style id for
            # deterministic output.
            scored.sort(key=lambda item: (-item[0], item[1]))
            if top_k <= 0:
                top_k = len(scored)
            result: List[CognitiveStyle] = []
            for score, other_id in scored[:top_k]:
                style = self._styles.get(other_id)
                if style is not None:
                    result.append(style)
            return result

    # ── Style Transfer ─────────────────────────────────────────────

    def create_transfer(
        self,
        source_style_id: str,
        target_domain: str,
        fidelity: FidelityMode = FidelityMode.ADAPTIVE,
        description: str = "",
    ) -> StyleTransfer:
        """Create a style transfer request from a source style to a target.

        The transfer starts in PENDING status. The source style must
        already be registered; if it has no fingerprint, one is built
        automatically so the transfer can be validated later.

        Raises:
            KeyError: when the source style is not registered.
        """
        with self._lock:
            if source_style_id not in self._styles:
                raise KeyError(f"Style not found: {source_style_id}")
            if len(self._transfers) >= self.MAX_TRANSFERS:
                self._evict_oldest_transfer_locked()
            # Ensure the source style has a fingerprint for later validation.
            if source_style_id not in self._fingerprints:
                self._build_fingerprint_locked(source_style_id)
            coerced_fidelity = _coerce_enum(fidelity, FidelityMode)
            transfer = StyleTransfer(
                source_style_id=source_style_id,
                target_domain=target_domain,
                fidelity=coerced_fidelity,
                description=description,
                status=TransferStatus.PENDING,
            )
            self._transfers[transfer.transfer_id] = transfer
            return transfer

    def get_transfer(self, transfer_id: str) -> Optional[StyleTransfer]:
        """Retrieve a style transfer by its identifier."""
        with self._lock:
            return self._transfers.get(transfer_id)

    def list_transfers(
        self,
        status: Optional[TransferStatus] = None,
    ) -> List[StyleTransfer]:
        """List transfers, optionally filtered by status.

        Args:
            status: Optional TransferStatus (or string name) to filter by.

        Returns:
            A list of matching StyleTransfer objects.
        """
        with self._lock:
            if status is None:
                return list(self._transfers.values())
            coerced = _coerce_enum(status, TransferStatus)
            return [t for t in self._transfers.values() if t.status == coerced]

    def validate_transfer(
        self,
        transfer_id: str,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> StyleTransfer:
        """Validate a transfer against constraints and mark it completed.

        The transfer's status is set to COMPLETED and a validation_status
        is computed from the constraints. Supported constraints:
          - "min_dimensions": minimum number of covered dimensions.
          - "min_total_weight": minimum sum of feature weights.
          - "max_total_weight": maximum sum of feature weights.
          - "required_dimensions": list of dimension names that must be
            covered.

        When no constraints are supplied, the transfer passes if the
        source style has at least one feature. When some constraints pass
        and some fail, the validation status is PARTIAL.

        Raises:
            KeyError: when the transfer_id is not registered.
        """
        with self._lock:
            transfer = self._transfers.get(transfer_id)
            if transfer is None:
                raise KeyError(f"Transfer not found: {transfer_id}")
            style = self._styles.get(transfer.source_style_id)
            # Move through the lifecycle before settling on COMPLETED.
            transfer.status = TransferStatus.EXTRACTING
            transfer.status = TransferStatus.TRANSFERRING
            transfer.status = TransferStatus.VALIDATING
            notes_parts: List[str] = []
            passed = 0
            failed = 0
            total_checks = 0
            if style is None:
                transfer.validation_status = ValidationStatus.FAILED
                transfer.validation_notes = "Source style no longer exists."
                transfer.status = TransferStatus.COMPLETED
                transfer.completed_at = datetime.utcnow().isoformat()
                return transfer
            dimensions_covered = {f.dimension for f in style.features}
            total_weight = sum(f.weight for f in style.features)
            if constraints is None:
                constraints = {}
            # Check min_dimensions.
            if "min_dimensions" in constraints:
                total_checks += 1
                required = int(constraints["min_dimensions"])
                if len(dimensions_covered) >= required:
                    passed += 1
                    notes_parts.append(
                        f"min_dimensions={required} satisfied "
                        f"({len(dimensions_covered)} covered)"
                    )
                else:
                    failed += 1
                    notes_parts.append(
                        f"min_dimensions={required} not satisfied "
                        f"({len(dimensions_covered)} covered)"
                    )
            # Check min_total_weight.
            if "min_total_weight" in constraints:
                total_checks += 1
                required = float(constraints["min_total_weight"])
                if total_weight >= required:
                    passed += 1
                    notes_parts.append(
                        f"min_total_weight={required} satisfied "
                        f"(total={total_weight:.3f})"
                    )
                else:
                    failed += 1
                    notes_parts.append(
                        f"min_total_weight={required} not satisfied "
                        f"(total={total_weight:.3f})"
                    )
            # Check max_total_weight.
            if "max_total_weight" in constraints:
                total_checks += 1
                limit = float(constraints["max_total_weight"])
                if total_weight <= limit:
                    passed += 1
                    notes_parts.append(
                        f"max_total_weight={limit} satisfied "
                        f"(total={total_weight:.3f})"
                    )
                else:
                    failed += 1
                    notes_parts.append(
                        f"max_total_weight={limit} not satisfied "
                        f"(total={total_weight:.3f})"
                    )
            # Check required_dimensions.
            if "required_dimensions" in constraints:
                total_checks += 1
                required_dims = constraints["required_dimensions"]
                if not isinstance(required_dims, (list, tuple)):
                    required_dims = [required_dims]
                missing: List[str] = []
                for raw_dim in required_dims:
                    try:
                        dim = _coerce_enum(raw_dim, StyleDimension)
                    except ValueError:
                        missing.append(str(raw_dim))
                        continue
                    if dim not in dimensions_covered:
                        missing.append(dim.value)
                if not missing:
                    passed += 1
                    notes_parts.append(
                        f"required_dimensions all covered "
                        f"({len(required_dims)} checked)"
                    )
                else:
                    failed += 1
                    notes_parts.append(
                        f"required_dimensions missing: {', '.join(missing)}"
                    )
            # When no constraints were supplied, fall back to a sanity check.
            if total_checks == 0:
                total_checks = 1
                if style.features:
                    passed += 1
                    notes_parts.append(
                        f"source style has {len(style.features)} feature(s)"
                    )
                else:
                    failed += 1
                    notes_parts.append("source style has no features")
            # Determine the aggregate validation status.
            if failed == 0:
                transfer.validation_status = ValidationStatus.PASSED
            elif passed == 0:
                transfer.validation_status = ValidationStatus.FAILED
            else:
                transfer.validation_status = ValidationStatus.PARTIAL
            notes_parts.append(f"fidelity={transfer.fidelity.value}")
            transfer.validation_notes = "; ".join(notes_parts)
            transfer.status = TransferStatus.COMPLETED
            transfer.completed_at = datetime.utcnow().isoformat()
            return transfer

    # ── Style Blending ─────────────────────────────────────────────

    def blend_styles(
        self,
        style_ids: List[str],
        strategy: BlendStrategy = BlendStrategy.WEIGHTED,
        weights: Optional[List[float]] = None,
    ) -> StyleBlend:
        """Combine several styles into a composite style.

        The ``strategy`` determines how features are merged:
          - WEIGHTED: features from each style contribute in proportion to
            the supplied weights (or equal weights when omitted).
          - DOMINANT: the first style's features dominate; later styles
            contribute only dimensions the first style does not cover.
          - MOSAIC: each dimension is taken from a single source style,
            rotating through the inputs in order.
          - NOVEL: average each dimension across all input styles to
            produce a fresh profile.

        The resulting CognitiveStyle is registered with the engine and
        referenced by ``resulting_style_id`` on the returned StyleBlend.

        Raises:
            ValueError: when no style_ids are supplied or any id is missing.
        """
        with self._lock:
            if not style_ids:
                raise ValueError("blend_styles requires at least one style_id")
            sources: List[CognitiveStyle] = []
            for sid in style_ids:
                style = self._styles.get(sid)
                if style is None:
                    raise ValueError(f"Style not found: {sid}")
                sources.append(style)
            coerced_strategy = _coerce_enum(strategy, BlendStrategy)
            # Normalize weights to the same length as style_ids.
            if weights is None:
                norm_weights = [1.0 / len(sources)] * len(sources)
            else:
                if len(weights) != len(sources):
                    norm_weights = list(weights[: len(sources)])
                    while len(norm_weights) < len(sources):
                        norm_weights.append(0.0)
                else:
                    norm_weights = list(weights)
            weight_sum = sum(norm_weights)
            if weight_sum <= 0.0:
                norm_weights = [1.0 / len(sources)] * len(sources)
                weight_sum = 1.0
            norm_weights = [w / weight_sum for w in norm_weights]
            merged_features = self._merge_features_locked(
                sources, coerced_strategy, norm_weights
            )
            description_parts = [
                f"{s.source_id}:{s.style_id}" for s in sources
            ]
            new_style = CognitiveStyle(
                source_id="blend",
                source_type=SourceType.TEMPLATE,
                description=(
                    f"Blended style ({coerced_strategy.value}) from "
                    + ", ".join(description_parts)
                ),
                features=merged_features,
            )
            if len(self._styles) >= self.MAX_STYLES:
                self._evict_oldest_style_locked()
            self._styles[new_style.style_id] = new_style
            stored_weights = list(weights) if weights is not None else list(norm_weights)
            blend = StyleBlend(
                style_ids=list(style_ids),
                strategy=coerced_strategy,
                weights=stored_weights,
                resulting_style_id=new_style.style_id,
                description=new_style.description,
            )
            if len(self._blends) >= self.MAX_BLENDS:
                self._evict_oldest_blend_locked()
            self._blends[blend.blend_id] = blend
            return blend

    def get_blend(self, blend_id: str) -> Optional[StyleBlend]:
        """Retrieve a style blend by its identifier."""
        with self._lock:
            return self._blends.get(blend_id)

    def list_blends(self) -> List[StyleBlend]:
        """List all registered style blends."""
        with self._lock:
            return list(self._blends.values())

    # ── Style Application ──────────────────────────────────────────

    def apply_style(
        self,
        style_id: str,
        problem_description: str,
    ) -> Dict[str, Any]:
        """Apply a cognitive style to a problem and return a suggested approach.

        The returned dict includes the style's dominant dimension, a
        textual approach recommendation, a list of heuristics drawn from
        the style's features, an ordered step sequence, and the
        processing time taken.

        Raises:
            KeyError: when the style_id is not registered.
        """
        with self._lock:
            start = time.time()
            style = self._styles.get(style_id)
            if style is None:
                raise KeyError(f"Style not found: {style_id}")
            # Rank features by weight to find the dominant dimensions.
            ranked = sorted(
                style.features, key=lambda f: f.weight, reverse=True
            )
            if ranked:
                primary_dimension = ranked[0].dimension.value
            else:
                primary_dimension = StyleDimension.ANALYTICAL.value
            heuristics: List[str] = []
            for feat in ranked:
                label = feat.dimension.value
                hint = feat.description or f"lean on {label} reasoning"
                heuristics.append(f"{label} ({feat.weight:.2f}): {hint}")
            steps = self._derive_steps_locked(primary_dimension, ranked)
            approach = self._approach_text_locked(primary_dimension, style)
            elapsed = time.time() - start
            return {
                "style_id": style_id,
                "problem_description": problem_description,
                "primary_dimension": primary_dimension,
                "approach": approach,
                "heuristics": heuristics,
                "step_sequence": steps,
                "fidelity_hint": "preserve dominant dimensions first",
                "processing_time": elapsed,
            }

    # ── Statistics & Maintenance ───────────────────────────────────

    def get_stats(self) -> TransferStats:
        """Compute aggregate statistics over the engine's current state."""
        with self._lock:
            total_styles = len(self._styles)
            total_transfers = len(self._transfers)
            completed_transfers = sum(
                1 for t in self._transfers.values()
                if t.status == TransferStatus.COMPLETED
            )
            total_blends = len(self._blends)
            by_source: Dict[str, int] = {}
            by_dimension: Dict[str, int] = {}
            for style in self._styles.values():
                src_key = (
                    style.source_type.value
                    if isinstance(style.source_type, SourceType)
                    else str(style.source_type)
                )
                by_source[src_key] = by_source.get(src_key, 0) + 1
                covered: set = set()
                for feat in style.features:
                    dim_key = (
                        feat.dimension.value
                        if isinstance(feat.dimension, StyleDimension)
                        else str(feat.dimension)
                    )
                    covered.add(dim_key)
                for dim_key in covered:
                    by_dimension[dim_key] = by_dimension.get(dim_key, 0) + 1
            return TransferStats(
                total_styles=total_styles,
                total_transfers=total_transfers,
                completed_transfers=completed_transfers,
                total_blends=total_blends,
                styles_by_source=by_source,
                styles_by_dimension=by_dimension,
            )

    def reset(self) -> None:
        """Clear all in-memory state on this engine instance."""
        with self._lock:
            self._styles.clear()
            self._fingerprints.clear()
            self._transfers.clear()
            self._blends.clear()

    # ── Internal helpers (caller must hold self._lock) ─────────────

    def _parse_features_locked(
        self,
        features: Optional[List[Dict[str, Any]]],
    ) -> List[StyleFeature]:
        """Convert a list of feature dicts into StyleFeature objects.

        Each dict may carry "dimension" (StyleDimension or string),
        "weight" (float, clamped to [0, 1]), and "description" (str).
        Non-dict entries are skipped. Caller must hold the lock.
        """
        parsed: List[StyleFeature] = []
        if not features:
            return parsed
        for raw in features:
            if not isinstance(raw, dict):
                continue
            dimension = _coerce_enum(
                raw.get("dimension", "analytical"), StyleDimension
            )
            weight = _clamp(float(raw.get("weight", 0.5)))
            feat_desc = str(raw.get("description", ""))
            parsed.append(
                StyleFeature(
                    dimension=dimension,
                    weight=weight,
                    description=feat_desc,
                )
            )
        return parsed

    def _build_fingerprint_locked(self, style_id: str) -> StyleFingerprint:
        """Build and cache a fingerprint for a style.

        The fingerprint vector has one entry per dimension in
        ``_STYLE_DIMENSION_ORDER``; each entry is the summed weight of
        the style's features in that dimension. Caller must hold the lock.

        Raises:
            KeyError: when the style_id is not registered.
        """
        style = self._styles.get(style_id)
        if style is None:
            raise KeyError(f"Style not found: {style_id}")
        vector = [0.0] * len(_STYLE_DIMENSION_ORDER)
        covered: List[str] = []
        for idx, dim in enumerate(_STYLE_DIMENSION_ORDER):
            total = 0.0
            for feat in style.features:
                if feat.dimension == dim:
                    total += feat.weight
            vector[idx] = total
            if total > 0.0:
                covered.append(dim.value)
        fingerprint = StyleFingerprint(
            style_id=style_id,
            vector=vector,
            dimensions_covered=covered,
        )
        self._fingerprints[style_id] = fingerprint
        style.fingerprint_id = fingerprint.fingerprint_id
        return fingerprint

    def _merge_features_locked(
        self,
        sources: List[CognitiveStyle],
        strategy: BlendStrategy,
        weights: List[float],
    ) -> List[StyleFeature]:
        """Merge feature lists from several styles per the blend strategy.

        Returns a list of StyleFeature objects, one per covered dimension,
        with weights clamped to [0, 1]. Caller must hold the lock.
        """
        dim_totals: Dict[StyleDimension, float] = {
            dim: 0.0 for dim in _STYLE_DIMENSION_ORDER
        }
        dim_descriptions: Dict[StyleDimension, List[str]] = {
            dim: [] for dim in _STYLE_DIMENSION_ORDER
        }
        if strategy == BlendStrategy.DOMINANT:
            # First style dominates; later styles only fill gaps.
            covered_dims: set = set()
            for idx, style in enumerate(sources):
                for feat in style.features:
                    if idx > 0 and feat.dimension in covered_dims:
                        continue
                    dim_totals[feat.dimension] += feat.weight
                    covered_dims.add(feat.dimension)
                    if feat.description:
                        dim_descriptions[feat.dimension].append(feat.description)
        elif strategy == BlendStrategy.MOSAIC:
            # Each dimension taken from the first source that claims it.
            for style in sources:
                for feat in style.features:
                    if dim_totals[feat.dimension] > 0.0:
                        continue
                    dim_totals[feat.dimension] = feat.weight
                    if feat.description:
                        dim_descriptions[feat.dimension].append(feat.description)
        elif strategy == BlendStrategy.NOVEL:
            # Average each dimension across all contributing sources.
            counts: Dict[StyleDimension, int] = {
                dim: 0 for dim in _STYLE_DIMENSION_ORDER
            }
            for style in sources:
                for feat in style.features:
                    dim_totals[feat.dimension] += feat.weight
                    counts[feat.dimension] += 1
                    if feat.description:
                        dim_descriptions[feat.dimension].append(feat.description)
            for dim in _STYLE_DIMENSION_ORDER:
                if counts[dim] > 0:
                    dim_totals[dim] = dim_totals[dim] / counts[dim]
        else:
            # WEIGHTED: sum weighted contributions per dimension.
            for idx, style in enumerate(sources):
                w = weights[idx] if idx < len(weights) else 0.0
                for feat in style.features:
                    dim_totals[feat.dimension] += feat.weight * w
                    if feat.description:
                        dim_descriptions[feat.dimension].append(feat.description)
        # Build the merged feature list, skipping zero-weight dimensions.
        merged: List[StyleFeature] = []
        for dim in _STYLE_DIMENSION_ORDER:
            total = dim_totals[dim]
            if total <= 0.0:
                continue
            desc = " | ".join(dim_descriptions[dim]) if dim_descriptions[dim] else ""
            merged.append(
                StyleFeature(
                    dimension=dim,
                    weight=_clamp(total),
                    description=desc,
                )
            )
        return merged

    def _derive_steps_locked(
        self,
        primary_dimension: str,
        ranked: List[StyleFeature],
    ) -> List[str]:
        """Produce an ordered step sequence guided by the dominant dimension.

        The dominant dimension supplies the opening step; each remaining
        active dimension contributes its own step in ranked order. Two
        closing steps wrap up the sequence. Caller must hold the lock.
        """
        steps: List[str] = []
        opening = _DIMENSION_OPENING_STEPS.get(
            primary_dimension, "Frame the problem and its constraints"
        )
        steps.append(opening)
        seen: set = {primary_dimension}
        for feat in ranked:
            label = feat.dimension.value
            if label in seen:
                continue
            seen.add(label)
            template = _DIMENSION_OPENING_STEPS.get(
                label, f"Apply {label} reasoning to the current view"
            )
            steps.append(template)
        steps.append("Synthesize findings into a coherent answer")
        steps.append("Review the answer against the original problem")
        return steps

    def _approach_text_locked(
        self,
        primary_dimension: str,
        style: CognitiveStyle,
    ) -> str:
        """Compose a short approach recommendation. Caller holds the lock."""
        base = _DIMENSION_APPROACH_FRAGMENTS.get(
            primary_dimension,
            "Apply the style's dominant reasoning texture to the problem.",
        )
        feature_count = len(style.features)
        return (
            f"{base} The style draws on {feature_count} feature(s) "
            f"from source '{style.source_id}'."
        )

    def _evict_oldest_style_locked(self) -> None:
        """Remove the style with the oldest created_at. Caller holds lock."""
        if not self._styles:
            return
        oldest_id = min(
            self._styles.keys(),
            key=lambda sid: self._styles[sid].created_at,
        )
        self._styles.pop(oldest_id, None)
        self._fingerprints.pop(oldest_id, None)

    def _evict_oldest_transfer_locked(self) -> None:
        """Remove the transfer with the oldest created_at. Caller holds lock."""
        if not self._transfers:
            return
        oldest_id = min(
            self._transfers.keys(),
            key=lambda tid: self._transfers[tid].created_at,
        )
        self._transfers.pop(oldest_id, None)

    def _evict_oldest_blend_locked(self) -> None:
        """Remove the blend with the oldest created_at. Caller holds lock."""
        if not self._blends:
            return
        oldest_id = min(
            self._blends.keys(),
            key=lambda bid: self._blends[bid].created_at,
        )
        self._blends.pop(oldest_id, None)


# =========================================================
# Module-level singleton
# =========================================================

_engine: Optional[AgentCognitiveStyleTransfer] = None
_engine_lock = threading.Lock()


def get_style_transfer_engine() -> AgentCognitiveStyleTransfer:
    """Return the process-wide AgentCognitiveStyleTransfer singleton.

    The singleton is created lazily on first access and is safe to call
    from multiple threads. Subsequent calls return the same instance.
    """
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = AgentCognitiveStyleTransfer()
    return _engine


def reset_style_transfer_engine() -> None:
    """Reset the process-wide AgentCognitiveStyleTransfer singleton.

    Clears any in-memory state on the existing instance (if any) and
    drops the singleton reference so the next get_style_transfer_engine()
    call creates a fresh engine.
    """
    global _engine
    with _engine_lock:
        if _engine is not None:
            _engine.reset()
        _engine = None
