"""Agent Cognitive Entropy Engine — information-theoretic measurement of reasoning state.

Views an agent's internal state as a collection of probability distributions
(beliefs, reasoning traces, decisions, attention, knowledge) and computes
Shannon entropy for each. High entropy means uncertainty and exploration; low
entropy means certainty and commitment. The engine tracks entropy flux over
time, classifies the regime from RIGID through BALANCED to CHAOTIC, and applies
maximum entropy principles for inference under ignorance.

Architecture:
  AgentCognitiveEntropy (thread-safe singleton)
  ├── DistributionSample   (one sampled distribution + its entropies)
  ├── EntropyFluxRecord    (a delta between two consecutive samples)
  ├── InferenceResult      (a prior -> posterior inference under a principle)
  ├── CompressionTrace     (a simulated compression + its information loss)
  ├── EntropyProfile       (per-agent aggregate regime and distributions)
  └── EntropyStats         (engine-wide aggregate statistics)
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Dict, List


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class EntropyKind(str, Enum):
    """The cognitive subsystem a sampled distribution belongs to.

    Each kind corresponds to a different probabilistic surface inside the
    agent. BELIEF is the distribution over hypotheses the agent currently
    holds about the world. REASONING is the distribution over candidate
    next reasoning steps or sub-conclusions. DECISION is the distribution
    over actions the agent is about to choose among. ATTENTION is the
    distribution over inputs, contexts, or targets the agent is allocating
    focus to. KNOWLEDGE is the distribution over retrieved knowledge
    fragments weighted by relevance.
    """
    BELIEF = "belief"          # distribution over hypotheses
    REASONING = "reasoning"    # distribution over next reasoning steps
    DECISION = "decision"      # distribution over candidate actions
    ATTENTION = "attention"    # distribution over focus targets
    KNOWLEDGE = "knowledge"    # distribution over retrieved facts


class EntropyRegime(str, Enum):
    """Classification of an agent's cognitive state by entropy level.

    The regime is derived from the normalized entropy in [0, 1]. RIGID
    means the state is too ordered — the agent is overconfident and
    brittle. ORDERED is a healthy low-entropy state where the agent is
    confidently committed but not yet rigid. BALANCED is the optimal
    middle where the agent is confident enough to act and uncertain enough
    to revise. DISORDERED is an unhealthy high-entropy state where the
    agent is wavering. CHAOTIC means the state is too disordered — the
    agent is erratic and cannot settle.
    """
    RIGID = "rigid"            # too ordered, overconfident, brittle
    ORDERED = "ordered"        # healthy low entropy, confidently committed
    BALANCED = "balanced"      # optimal middle ground
    DISORDERED = "disordered"  # unhealthy high entropy, wavering
    CHAOTIC = "chaotic"        # too disordered, erratic, cannot settle


class FluxDirection(str, Enum):
    """The direction of entropy change between two consecutive samples.

    INCREASING means entropy is growing (the agent is becoming more
    uncertain or exploratory). DECREASING means entropy is falling (the
    agent is becoming more certain or exploitative). STABLE means entropy
    is roughly constant. FLUCTUATING means the recent deltas alternate in
    sign, indicating the agent is oscillating between certainty and
    uncertainty rather than converging.
    """
    INCREASING = "increasing"    # entropy growing, more uncertain
    DECREASING = "decreasing"    # entropy falling, more certain
    STABLE = "stable"            # entropy roughly constant
    FLUCTUATING = "fluctuating"  # deltas alternate sign, oscillating


class InferencePrinciple(str, Enum):
    """The information-theoretic principle used to derive a posterior.

    MAXIMUM_ENTROPY produces the uniform distribution over the support —
    the least-committal distribution consistent with what is known, used
    when the agent has no reason to prefer one outcome. PRINCIPLE_OF_INDIFFERENCE
    is the classical form of the same idea: assign equal probability to
    each indistinguishable outcome. MINIMUM_ENTROPY produces a sharply
    peaked distribution concentrated on the most likely outcome, used when
    the agent must commit. CROSS_ENTROPY_MIN blends the prior with
    evidence to minimize the cross-entropy between posterior and evidence.
    """
    MAXIMUM_ENTROPY = "maximum_entropy"            # uniform over support
    MINIMUM_ENTROPY = "minimum_entropy"            # peaked at argmax
    PRINCIPLE_OF_INDIFFERENCE = "principle_of_indifference"  # uniform
    CROSS_ENTROPY_MIN = "cross_entropy_min"        # blend prior with evidence


class CompressionStatus(str, Enum):
    """Outcome of a simulated payload compression.

    UNCOMPRESSED means the compression ratio is very high (barely any
    size reduction), typically because the source is already near-random
    or the model declined to compress. PARTIAL means some reduction was
    achieved but a large fraction of the payload remains. COMPRESSED
    means a healthy reduction was achieved. LOSSY means the compression
    discarded information to achieve its ratio.
    """
    UNCOMPRESSED = "uncompressed"  # barely reduced
    PARTIAL = "partial"            # some reduction
    COMPRESSED = "compressed"      # healthy reduction
    LOSSY = "lossy"                # information discarded


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _now() -> str:
    """Return an ISO-8601 UTC timestamp string."""
    return datetime.utcnow().isoformat()


def _new_id() -> str:
    """Generate a short unique identifier for a sample/record/result/etc."""
    return str(uuid.uuid4())[:8]


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a numeric value into the inclusive range [low, high].

    Non-numeric inputs are coerced to ``low`` so callers can pass loosely
    typed values without raising.
    """
    try:
        f = float(value)
    except (TypeError, ValueError):
        return low
    if f < low:
        return low
    if f > high:
        return high
    return f


def _enum_value(enum_cls: type, value: Any) -> str:
    """Return the ``.value`` of an enum member, or a string fallback.

    Used inside ``to_dict`` methods so a stored field always serializes to
    a plain string even if a non-enum slipped in through direct
    construction.
    """
    if isinstance(value, enum_cls):
        return value.value
    return str(value)


def _resolve_enum(enum_cls: type, value: Any) -> Any:
    """Resolve a value to an enum member, accepting name or value strings.

    Enum members are returned unchanged. Strings are matched first against
    member values (e.g. ``"belief"``) and then against member names (e.g.
    ``"BELIEF"``), so callers may pass either form. Raises ``ValueError``
    if neither matches.
    """
    if isinstance(value, enum_cls):
        return value
    if isinstance(value, str):
        try:
            return enum_cls(value)
        except ValueError:
            pass
        try:
            return enum_cls[value]
        except KeyError:
            pass
    raise ValueError(f"{value!r} is not a valid {enum_cls.__name__}")


def _shannon_entropy(dist: Dict[str, float]) -> float:
    """Compute the Shannon entropy (in bits) of a distribution.

    Returns ``-sum(p * log2(p))`` over all positive probabilities. Zero or
    negative masses are skipped (a zero mass contributes nothing to
    entropy). The input need not be normalized — but if it is not, the
    result is not a true Shannon entropy; callers should normalize first
    when a proper entropy is required.
    """
    total = 0.0
    for v in dist.values():
        try:
            p = float(v)
        except (TypeError, ValueError):
            continue
        if p > 0.0:
            total += p * math.log2(p)
    return -total if total != 0.0 else 0.0


def _max_entropy(n: int) -> float:
    """Return the maximum possible Shannon entropy for ``n`` outcomes.

    The maximum entropy of a discrete distribution over ``n`` outcomes is
    ``log2(n)``, achieved by the uniform distribution. Returns ``0.0`` for
    ``n <= 1`` since a single-outcome (or empty) distribution has no
    uncertainty.
    """
    if n > 1:
        return math.log2(n)
    return 0.0


def _normalized_entropy(dist: Dict[str, float]) -> float:
    """Return the Shannon entropy of ``dist`` normalized to [0, 1].

    The normalization divides the Shannon entropy by the maximum possible
    entropy for the support size, so 0 means a fully concentrated (delta)
    distribution and 1 means a uniform distribution. Returns 0.0 for
    empty or single-outcome distributions.
    """
    shannon = _shannon_entropy(dist)
    max_h = _max_entropy(len(dist))
    if max_h <= 0.0:
        return 0.0
    ratio = shannon / max_h
    if ratio < 0.0:
        return 0.0
    if ratio > 1.0:
        return 1.0
    return ratio


def _determine_regime(normalized: float) -> EntropyRegime:
    """Classify a normalized entropy value into an entropy regime.

    The thresholds partition [0, 1] into five bands: below 0.2 is RIGID
    (too ordered), below 0.4 is ORDERED (healthy low), below 0.6 is
    BALANCED (optimal), below 0.8 is DISORDERED (unhealthy high), and
    0.8 and above is CHAOTIC (too disordered). The input is clamped to
    [0, 1] so out-of-range values are treated as the nearest extreme.
    """
    n = _clamp(normalized, 0.0, 1.0)
    if n < 0.2:
        return EntropyRegime.RIGID
    if n < 0.4:
        return EntropyRegime.ORDERED
    if n < 0.6:
        return EntropyRegime.BALANCED
    if n < 0.8:
        return EntropyRegime.DISORDERED
    return EntropyRegime.CHAOTIC


def _kl_divergence(p: Dict[str, float], q: Dict[str, float]) -> float:
    """Compute the Kullback-Leibler divergence ``KL(p || q)`` in bits.

    Sums ``p_i * log2(p_i / q_i)`` over keys present in both distributions
    where both values are strictly positive. Keys missing from ``q`` (or
    with zero mass in ``q``) are skipped, since they would make the log
    term undefined; this is a standard practical convention for discrete
    KL. Returns 0.0 if there is no overlapping positive support.
    """
    total = 0.0
    for key, pv in p.items():
        try:
            pi = float(pv)
        except (TypeError, ValueError):
            continue
        if pi <= 0.0:
            continue
        qv = q.get(key)
        if qv is None:
            continue
        try:
            qi = float(qv)
        except (TypeError, ValueError):
            continue
        if qi <= 0.0:
            continue
        total += pi * math.log2(pi / qi)
    return total


def _normalize_distribution(dist: Dict[str, float]) -> Dict[str, float]:
    """Return a normalized copy of ``dist`` with values summing to 1.

    Non-positive and non-numeric values are dropped. If the total mass is
    zero (or the input is empty), an empty dict is returned. This is the
    safe entry point for any distribution that will be fed into an
    entropy or divergence computation.
    """
    if not dist:
        return {}
    positive: Dict[str, float] = {}
    for k, v in dist.items():
        try:
            fv = float(v)
        except (TypeError, ValueError):
            continue
        if fv > 0.0:
            positive[k] = fv
    total = sum(positive.values())
    if total <= 0.0:
        return {}
    return {k: v / total for k, v in positive.items()}


def _peaked_distribution(dist: Dict[str, float]) -> Dict[str, float]:
    """Return a sharply peaked distribution concentrated on the argmax.

    The most probable key receives the bulk of the mass (0.95); the
    remaining 0.05 is spread equally over the other keys. This keeps the
    distribution proper (sums to 1) and avoids zero probabilities, which
    would make KL divergence undefined. Used for MINIMUM_ENTROPY inference
    where the agent must commit to a single most-likely outcome.
    """
    items = [(k, v) for k, v in dist.items() if v > 0]
    if not items:
        return {}
    if len(items) == 1:
        return {items[0][0]: 1.0}
    argmax_key = max(items, key=lambda kv: kv[1])[0]
    others = [k for k, _ in items if k != argmax_key]
    peak = 0.95
    rest = (1.0 - peak) / len(others) if others else 0.0
    result: Dict[str, float] = {k: rest for k in others}
    result[argmax_key] = peak
    return result


def _blend_distributions(
    p: Dict[str, float],
    q: Dict[str, float],
    alpha: float = 0.5,
) -> Dict[str, float]:
    """Blend two distributions as ``alpha*p + (1-alpha)*q`` over their union.

    Missing keys are treated as zero mass. The result is renormalized to
    sum to 1 so it remains a proper distribution even when the supports
    differ. Used for CROSS_ENTROPY_MIN inference, where the posterior is a
    compromise between the prior and the evidence.
    """
    keys = set(p.keys()) | set(q.keys())
    a = _clamp(alpha, 0.0, 1.0)
    blended: Dict[str, float] = {}
    for k in keys:
        blended[k] = a * p.get(k, 0.0) + (1.0 - a) * q.get(k, 0.0)
    return _normalize_distribution(blended)


def _sign(x: float) -> int:
    """Return the sign of ``x`` as -1, 0, or 1, with a tiny epsilon.

    Values within ``1e-9`` of zero are treated as zero so that floating
    point noise does not produce spurious signs.
    """
    if x > 1e-9:
        return 1
    if x < -1e-9:
        return -1
    return 0


def _alternates_sign(deltas: List[float], n: int = 3) -> bool:
    """Return True if the last ``n`` deltas alternate in sign.

    Used to detect fluctuation: a sequence like +, -, + or -, +, - means
    the agent is oscillating rather than converging. Any zero sign (a
    flat delta) breaks alternation and returns False. Returns False if
    fewer than ``n`` deltas are available.
    """
    if len(deltas) < n:
        return False
    recent = deltas[-n:]
    signs = [_sign(d) for d in recent]
    if 0 in signs:
        return False
    for i in range(1, len(signs)):
        if signs[i] == signs[i - 1]:
            return False
    return True


def _empty_regime_distribution() -> Dict[EntropyRegime, int]:
    """Return a fresh regime counter initialized to zero for every regime."""
    return {regime: 0 for regime in EntropyRegime}


def _empty_kind_distribution() -> Dict[EntropyKind, int]:
    """Return a fresh kind counter initialized to zero for every kind."""
    return {kind: 0 for kind in EntropyKind}


def _empty_flux_direction_distribution() -> Dict[FluxDirection, int]:
    """Return a fresh direction counter initialized to zero for every direction."""
    return {d: 0 for d in FluxDirection}


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class DistributionSample:
    """A single sampled distribution from an agent's cognitive subsystem.

    A ``DistributionSample`` captures one point-in-time probability
    distribution from the agent, together with the entropy metrics
    computed from it. ``distribution`` is the raw mapping from outcome
    keys to probabilities (need not be normalized on input; the engine
    normalizes before computing metrics). ``shannon_entropy`` is the
    entropy in bits. ``max_entropy`` is ``log2(n)`` for the support size.
    ``normalized_entropy`` is ``shannon / max`` clamped to [0, 1], and is
    the canonical quantity used for regime classification.
    """
    sample_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    kind: EntropyKind = EntropyKind.BELIEF
    distribution: Dict[str, float] = field(default_factory=dict)
    shannon_entropy: float = 0.0
    normalized_entropy: float = 0.0
    max_entropy: float = 0.0
    sampled_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this sample to a plain dict, expanding the enum.

        The ``distribution`` dict is shallow-copied so the serialized form
        is independent of the live sample.
        """
        return {
            "sample_id": self.sample_id,
            "agent_id": self.agent_id,
            "kind": _enum_value(EntropyKind, self.kind),
            "distribution": dict(self.distribution),
            "shannon_entropy": self.shannon_entropy,
            "normalized_entropy": self.normalized_entropy,
            "max_entropy": self.max_entropy,
            "sampled_at": self.sampled_at,
        }


@dataclass
class EntropyFluxRecord:
    """A record of entropy change between two consecutive samples.

    A flux record is created each time the agent's entropy for a given
    kind is re-measured. ``previous_entropy`` is the entropy seen last
    time (or equal to ``current_entropy`` on the first measurement).
    ``delta`` is ``current - previous``. ``direction`` classifies the
    delta as INCREASING, DECREASING, STABLE, or FLUCTUATING (when the
    last few deltas alternate sign). ``velocity`` is the rate of change
    per unit sample interval (delta divided by elapsed time), giving a
    time-normalized sense of how fast the agent's uncertainty is moving.
    """
    record_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    kind: EntropyKind = EntropyKind.BELIEF
    previous_entropy: float = 0.0
    current_entropy: float = 0.0
    delta: float = 0.0
    direction: FluxDirection = FluxDirection.STABLE
    velocity: float = 0.0
    recorded_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this flux record to a plain dict, expanding enums."""
        return {
            "record_id": self.record_id,
            "agent_id": self.agent_id,
            "kind": _enum_value(EntropyKind, self.kind),
            "previous_entropy": self.previous_entropy,
            "current_entropy": self.current_entropy,
            "delta": self.delta,
            "direction": _enum_value(FluxDirection, self.direction),
            "velocity": self.velocity,
            "recorded_at": self.recorded_at,
        }


@dataclass
class InferenceResult:
    """The outcome of applying an inference principle to a prior.

    Records the ``principle`` used, the ``prior_distribution`` it started
    from, and the ``posterior_distribution`` it produced. ``info_gain`` is
    the reduction in entropy from prior to posterior
    (``H(prior) - H(posterior)``); a positive value means the inference
    reduced uncertainty, a negative value means it increased uncertainty
    (e.g. maximum-entropy inference deliberately spreads mass). ``kl_divergence``
    is ``KL(prior || posterior)``, a non-negative measure of how far the
    posterior moved from the prior. ``rationale`` is a free-form
    explanation supplied by the caller.
    """
    result_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    principle: InferencePrinciple = InferencePrinciple.MAXIMUM_ENTROPY
    prior_distribution: Dict[str, float] = field(default_factory=dict)
    posterior_distribution: Dict[str, float] = field(default_factory=dict)
    info_gain: float = 0.0
    kl_divergence: float = 0.0
    rationale: str = ""
    computed_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this inference result to a plain dict, expanding the enum.

        The ``prior_distribution`` and ``posterior_distribution`` dicts are
        shallow-copied so the serialized form is independent of the live
        result.
        """
        return {
            "result_id": self.result_id,
            "agent_id": self.agent_id,
            "principle": _enum_value(InferencePrinciple, self.principle),
            "prior_distribution": dict(self.prior_distribution),
            "posterior_distribution": dict(self.posterior_distribution),
            "info_gain": self.info_gain,
            "kl_divergence": self.kl_divergence,
            "rationale": self.rationale,
            "computed_at": self.computed_at,
        }


@dataclass
class CompressionTrace:
    """A trace of one simulated payload compression.

    Records the ``source_payload_size`` and ``compressed_size`` in bytes
    (or characters, depending on input), the ``ratio`` of compressed to
    source size, and the resulting ``status``. ``entropy_before`` is the
    normalized entropy of the source (in [0, 1]) supplied by the caller.
    ``entropy_after`` is the modeled aggregate entropy of the compressed
    payload. ``information_loss`` is the entropy discarded during
    compression — zero for lossless compression, positive for lossy.
    """
    trace_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    source_payload_size: int = 0
    compressed_size: int = 0
    ratio: float = 0.0
    status: CompressionStatus = CompressionStatus.UNCOMPRESSED
    entropy_before: float = 0.0
    entropy_after: float = 0.0
    information_loss: float = 0.0
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this compression trace to a plain dict, expanding the enum."""
        return {
            "trace_id": self.trace_id,
            "agent_id": self.agent_id,
            "source_payload_size": self.source_payload_size,
            "compressed_size": self.compressed_size,
            "ratio": self.ratio,
            "status": _enum_value(CompressionStatus, self.status),
            "entropy_before": self.entropy_before,
            "entropy_after": self.entropy_after,
            "information_loss": self.information_loss,
            "created_at": self.created_at,
        }


@dataclass
class EntropyProfile:
    """Per-agent aggregate entropy profile.

    A profile summarizes one agent's cognitive entropy posture. ``regime``
    is the agent's overall classification (RIGID through CHAOTIC).
    ``avg_entropy`` and ``avg_normalized`` are the mean Shannon and
    normalized entropies across the agent's samples. ``flux_volatility``
    measures how violently the agent's entropy has been changing (a
    function of recent flux delta magnitudes). ``samples_count`` is how
    many samples contributed. ``regime_distribution`` tallies samples by
    their regime, and ``kind_distribution`` tallies samples by their
    entropy kind, so callers can see where the agent's disorder is
    concentrated.
    """
    agent_id: str = ""
    regime: EntropyRegime = EntropyRegime.BALANCED
    avg_entropy: float = 0.0
    avg_normalized: float = 0.0
    flux_volatility: float = 0.0
    samples_count: int = 0
    regime_distribution: Dict[EntropyRegime, int] = field(
        default_factory=_empty_regime_distribution
    )
    kind_distribution: Dict[EntropyKind, int] = field(
        default_factory=_empty_kind_distribution
    )
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict.

        The ``regime`` enum is expanded via ``.value``. The
        ``regime_distribution`` and ``kind_distribution`` dicts are
        re-keyed by their enum ``.value`` strings so the serialized form
        is JSON-friendly.
        """
        return {
            "agent_id": self.agent_id,
            "regime": _enum_value(EntropyRegime, self.regime),
            "avg_entropy": self.avg_entropy,
            "avg_normalized": self.avg_normalized,
            "flux_volatility": self.flux_volatility,
            "samples_count": self.samples_count,
            "regime_distribution": {
                _enum_value(EntropyRegime, k): v
                for k, v in self.regime_distribution.items()
            },
            "kind_distribution": {
                _enum_value(EntropyKind, k): v
                for k, v in self.kind_distribution.items()
            },
            "updated_at": self.updated_at,
        }


@dataclass
class EntropyStats:
    """Engine-wide aggregate statistics.

    Counts of samples, flux records, inferences, and compressions across
    all agents. ``avg_shannon_entropy`` and ``avg_normalized_entropy`` are
    the mean Shannon and normalized entropies across all samples.
    ``regime_distribution`` tallies all samples by their regime.
    ``flux_direction_distribution`` tallies all flux records by their
    direction. The breakdown dicts are keyed by enum ``.value`` strings in
    the serialized form so the stats serialize cleanly to JSON.
    """
    total_samples: int = 0
    total_flux_records: int = 0
    total_inferences: int = 0
    total_compressions: int = 0
    avg_shannon_entropy: float = 0.0
    avg_normalized_entropy: float = 0.0
    regime_distribution: Dict[EntropyRegime, int] = field(
        default_factory=_empty_regime_distribution
    )
    flux_direction_distribution: Dict[FluxDirection, int] = field(
        default_factory=_empty_flux_direction_distribution
    )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict.

        The ``regime_distribution`` and ``flux_direction_distribution``
        dicts are re-keyed by their enum ``.value`` strings so the
        serialized form is JSON-friendly.
        """
        return {
            "total_samples": self.total_samples,
            "total_flux_records": self.total_flux_records,
            "total_inferences": self.total_inferences,
            "total_compressions": self.total_compressions,
            "avg_shannon_entropy": self.avg_shannon_entropy,
            "avg_normalized_entropy": self.avg_normalized_entropy,
            "regime_distribution": {
                _enum_value(EntropyRegime, k): v
                for k, v in self.regime_distribution.items()
            },
            "flux_direction_distribution": {
                _enum_value(FluxDirection, k): v
                for k, v in self.flux_direction_distribution.items()
            },
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveEntropy:
    """Thread-safe engine for measuring agent cognitive entropy.

    The engine maintains registries of distribution samples, entropy flux
    records, inference results, compression traces, and per-agent
    profiles. Each sampled distribution is reduced to its Shannon and
    normalized entropies; consecutive samples for the same agent and kind
    are diffed into flux records that track the direction and velocity of
    entropy change. Inference principles (maximum entropy, principle of
    indifference, minimum entropy, cross-entropy minimization) derive
    posteriors from priors under different assumptions. Payload
    compression is traced as an information-theoretic operation whose
    achievable ratio is bounded by the source entropy.

    All state mutations are guarded by a single reentrant lock so the
    engine is safe to call from multiple threads. The reentrant lock
    allows public methods to delegate to one another (for example,
    ``update_profile`` calls ``get_or_create_profile``) without
    self-deadlock.
    """

    # Delta threshold (in normalized entropy units) below which a change is
    # considered noise rather than a genuine increase or decrease.
    FLUX_DELTA_THRESHOLD: float = 0.01
    # Number of recent deltas inspected when detecting fluctuation.
    FLUX_WINDOW: int = 3
    # Blend weight for the prior in CROSS_ENTROPY_MIN inference. The
    # remaining weight goes to the evidence.
    BLEND_ALPHA: float = 0.5
    # Peak mass placed on the argmax in MINIMUM_ENTROPY inference.
    PEAK_MASS: float = 0.95

    def __init__(self) -> None:
        self._samples: Dict[str, DistributionSample] = {}
        self._flux_records: Dict[str, EntropyFluxRecord] = {}
        self._inferences: Dict[str, InferenceResult] = {}
        self._compressions: Dict[str, CompressionTrace] = {}
        self._profiles: Dict[str, EntropyProfile] = {}
        # Running integer counters, kept in sync with the registries above.
        self._stats: Dict[str, int] = {
            "total_samples": 0,
            "total_flux_records": 0,
            "total_inferences": 0,
            "total_compressions": 0,
        }
        # Last seen entropy per agent per kind, used to compute flux deltas.
        self._last_entropy: Dict[str, Dict[EntropyKind, float]] = {}
        # Last flux timestamp (as a float) per agent per kind, used to
        # compute flux velocity as delta / elapsed_time.
        self._last_flux_time: Dict[str, Dict[EntropyKind, float]] = {}
        # Recent flux deltas per agent per kind, used to detect fluctuation.
        self._flux_delta_history: Dict[str, Dict[EntropyKind, List[float]]] = {}
        # Reentrant lock so public methods may call one another safely.
        self._lock = threading.RLock()
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    # ── Distribution Sampling ──────────────────────────────────────

    def sample_distribution(
        self,
        agent_id: str,
        kind: Any,
        distribution: Dict[str, float],
    ) -> DistributionSample:
        """Sample a distribution and compute its entropy metrics.

        ``kind`` may be passed as an ``EntropyKind`` or its string
        name/value (e.g. ``"BELIEF"`` or ``"belief"``). The
        ``distribution`` mapping is normalized internally before computing
        metrics, so callers may pass unnormalized weights. Shannon entropy
        (in bits), maximum entropy for the support size, and normalized
        entropy (in [0, 1]) are all stored on the returned sample. The
        sample is registered in the engine and counted in the engine
        stats.
        """
        kind_enum = _resolve_enum(EntropyKind, kind)
        normalized = _normalize_distribution(distribution)
        shannon = _shannon_entropy(normalized)
        max_h = _max_entropy(len(normalized))
        norm_entropy = _normalized_entropy(normalized)
        with self._lock:
            sample = DistributionSample(
                agent_id=agent_id,
                kind=kind_enum,
                distribution=normalized,
                shannon_entropy=shannon,
                normalized_entropy=norm_entropy,
                max_entropy=max_h,
            )
            self._samples[sample.sample_id] = sample
            self._stats["total_samples"] += 1
            return sample

    def get_sample(self, sample_id: str) -> Optional[DistributionSample]:
        """Retrieve a sample by id, or ``None`` if absent."""
        with self._lock:
            return self._samples.get(sample_id)

    def list_samples(
        self,
        agent_id: Optional[str] = None,
        kind: Optional[Any] = None,
    ) -> List[DistributionSample]:
        """Return samples, optionally filtered by ``agent_id`` and ``kind``.

        When ``agent_id`` is ``None`` all samples are returned; otherwise
        only samples for that agent are returned. When ``kind`` is ``None``
        all kinds are returned; otherwise only samples of that kind are
        returned. ``kind`` may be passed as an ``EntropyKind`` or its
        string name/value. The returned list is a snapshot copy; mutating
        it does not affect the engine.
        """
        with self._lock:
            samples = list(self._samples.values())
        if agent_id is not None:
            samples = [s for s in samples if s.agent_id == agent_id]
        if kind is not None:
            kind_enum = _resolve_enum(EntropyKind, kind)
            samples = [s for s in samples if s.kind == kind_enum]
        return samples

    # ── Entropy Flux ───────────────────────────────────────────────

    def record_flux(
        self,
        agent_id: str,
        kind: Any,
        current_entropy: float,
    ) -> EntropyFluxRecord:
        """Record the change in entropy since the last sample for this kind.

        Looks up the previous entropy for ``(agent_id, kind)`` in the
        engine's internal last-entropy map. On the first call for a given
        agent/kind, the previous entropy defaults to the current entropy,
        producing a zero delta and a STABLE direction. The delta is
        classified as INCREASING (delta > 0.01), DECREASING (delta <
        -0.01), or STABLE (otherwise); if the last three deltas for this
        agent/kind alternate in sign, the direction is overridden to
        FLUCTUATING. Velocity is the delta divided by the elapsed sample
        interval (time since the previous flux record), or zero on the
        first call.
        """
        kind_enum = _resolve_enum(EntropyKind, kind)
        try:
            current = float(current_entropy)
        except (TypeError, ValueError):
            current = 0.0

        with self._lock:
            agent_last = self._last_entropy.setdefault(agent_id, {})
            agent_times = self._last_flux_time.setdefault(agent_id, {})
            agent_history = self._flux_delta_history.setdefault(agent_id, {})

            previous = agent_last.get(kind_enum)
            if previous is None:
                previous = current
            delta = current - previous

            now_ts = time.time()
            last_ts = agent_times.get(kind_enum)
            if last_ts is not None and now_ts > last_ts:
                velocity = delta / (now_ts - last_ts)
            else:
                velocity = 0.0

            # Append the current delta to history before checking
            # alternation, so the window includes this observation.
            history = agent_history.setdefault(kind_enum, [])
            history.append(delta)
            if len(history) > 64:
                # Bound the history to avoid unbounded growth.
                del history[: len(history) - 64]

            if _alternates_sign(history, self.FLUX_WINDOW):
                direction = FluxDirection.FLUCTUATING
            elif delta > self.FLUX_DELTA_THRESHOLD:
                direction = FluxDirection.INCREASING
            elif delta < -self.FLUX_DELTA_THRESHOLD:
                direction = FluxDirection.DECREASING
            else:
                direction = FluxDirection.STABLE

            record = EntropyFluxRecord(
                agent_id=agent_id,
                kind=kind_enum,
                previous_entropy=previous,
                current_entropy=current,
                delta=delta,
                direction=direction,
                velocity=velocity,
            )
            self._flux_records[record.record_id] = record
            self._stats["total_flux_records"] += 1

            # Update the last-entropy and last-time state for next time.
            agent_last[kind_enum] = current
            agent_times[kind_enum] = now_ts
            return record

    def get_flux_record(self, record_id: str) -> Optional[EntropyFluxRecord]:
        """Retrieve a flux record by id, or ``None`` if absent."""
        with self._lock:
            return self._flux_records.get(record_id)

    def list_flux_records(
        self,
        agent_id: Optional[str] = None,
        kind: Optional[Any] = None,
        direction: Optional[Any] = None,
    ) -> List[EntropyFluxRecord]:
        """Return flux records, optionally filtered.

        Filters by ``agent_id``, ``kind``, and ``direction``; any filter
        left as ``None`` matches all values for that field. ``kind`` and
        ``direction`` may be passed as enums or their string names/values.
        The returned list is a snapshot copy.
        """
        with self._lock:
            records = list(self._flux_records.values())
        if agent_id is not None:
            records = [r for r in records if r.agent_id == agent_id]
        if kind is not None:
            kind_enum = _resolve_enum(EntropyKind, kind)
            records = [r for r in records if r.kind == kind_enum]
        if direction is not None:
            direction_enum = _resolve_enum(FluxDirection, direction)
            records = [r for r in records if r.direction == direction_enum]
        return records

    # ── Inference ──────────────────────────────────────────────────

    def infer_distribution(
        self,
        agent_id: str,
        principle: Any,
        prior: Dict[str, float],
        evidence: Optional[Dict[str, float]] = None,
        rationale: str = "",
    ) -> InferenceResult:
        """Derive a posterior distribution from a prior under a principle.

        The ``principle`` selects the information-theoretic rule applied:

        - MAXIMUM_ENTROPY: the posterior is the uniform distribution over
          the prior's support. This is the least-committal distribution
          consistent with what is known; use it when the agent has no
          reason to prefer any outcome.
        - PRINCIPLE_OF_INDIFFERENCE: identical to maximum entropy — the
          classical statement that indistinguishable outcomes receive
          equal probability.
        - MINIMUM_ENTROPY: the posterior is a sharply peaked distribution
          concentrated on the prior's argmax, with a small residual
          spread over the remaining keys. Use it when the agent must
          commit to a single most-likely outcome.
        - CROSS_ENTROPY_MIN: the posterior is a blend of the prior and
          the evidence (``alpha * prior + (1 - alpha) * evidence``),
          renormalized. Use it when the agent must reconcile a prior
          belief with new evidence.

        ``info_gain`` is ``H(prior) - H(posterior)`` (positive when the
        inference reduced uncertainty, negative when it spread mass).
        ``kl_divergence`` is ``KL(prior || posterior)`` (always
        non-negative). The prior is normalized before inference; if the
        prior is empty, the posterior is also empty.
        """
        principle_enum = _resolve_enum(InferencePrinciple, principle)
        prior_norm = _normalize_distribution(prior)
        support = list(prior_norm.keys())

        if principle_enum in (
            InferencePrinciple.MAXIMUM_ENTROPY,
            InferencePrinciple.PRINCIPLE_OF_INDIFFERENCE,
        ):
            if support:
                u = 1.0 / len(support)
                posterior = {k: u for k in support}
            else:
                posterior = {}
        elif principle_enum == InferencePrinciple.MINIMUM_ENTROPY:
            posterior = _peaked_distribution(prior_norm)
        elif principle_enum == InferencePrinciple.CROSS_ENTROPY_MIN:
            if evidence:
                evidence_norm = _normalize_distribution(evidence)
                posterior = _blend_distributions(
                    prior_norm, evidence_norm, alpha=self.BLEND_ALPHA
                )
            else:
                posterior = dict(prior_norm)
        else:
            posterior = dict(prior_norm)

        info_gain = _shannon_entropy(prior_norm) - _shannon_entropy(posterior)
        kl = _kl_divergence(prior_norm, posterior)

        with self._lock:
            result = InferenceResult(
                agent_id=agent_id,
                principle=principle_enum,
                prior_distribution=prior_norm,
                posterior_distribution=posterior,
                info_gain=info_gain,
                kl_divergence=kl,
                rationale=rationale,
            )
            self._inferences[result.result_id] = result
            self._stats["total_inferences"] += 1
            return result

    def get_inference(self, result_id: str) -> Optional[InferenceResult]:
        """Retrieve an inference result by id, or ``None`` if absent."""
        with self._lock:
            return self._inferences.get(result_id)

    def list_inferences(
        self,
        agent_id: Optional[str] = None,
        principle: Optional[Any] = None,
    ) -> List[InferenceResult]:
        """Return inference results, optionally filtered.

        Filters by ``agent_id`` and ``principle``; either filter left as
        ``None`` matches all values for that field. ``principle`` may be
        passed as an ``InferencePrinciple`` or its string name/value. The
        returned list is a snapshot copy.
        """
        with self._lock:
            results = list(self._inferences.values())
        if agent_id is not None:
            results = [r for r in results if r.agent_id == agent_id]
        if principle is not None:
            principle_enum = _resolve_enum(InferencePrinciple, principle)
            results = [r for r in results if r.principle == principle_enum]
        return results

    # ── Compression ────────────────────────────────────────────────

    def compress_payload(
        self,
        agent_id: str,
        source_payload: Any,
        entropy_before: float,
    ) -> CompressionTrace:
        """Simulate compressing a payload and trace the information outcome.

        ``source_payload`` may be ``bytes`` or ``str``; its length is used
        as the source size. ``entropy_before`` is the normalized entropy
        of the source in [0, 1] (clamped); higher entropy means a more
        random source.

        The compression ratio is modeled as
        ``ratio = 0.6 + 0.3 * (1 - entropy_before)``, so the ratio scales
        with ``(1 - entropy_before)``. The compressed size is
        ``int(source_size * ratio)``. The status is derived from the
        ratio: above 0.85 is UNCOMPRESSED, above 0.7 is PARTIAL, above
        0.5 is COMPRESSED, otherwise LOSSY.

        ``entropy_after`` is the modeled aggregate entropy of the
        compressed payload, scaling with the retained size fraction
        (``entropy_before * ratio``). ``information_loss`` is zero for
        lossless compression (UNCOMPRESSED, PARTIAL, COMPRESSED) and
        equals the entropy discarded for LOSSY compression
        (``entropy_before * (1 - ratio)``).
        """
        try:
            source_size = len(source_payload)
        except TypeError:
            source_size = 0
        eb = _clamp(entropy_before, 0.0, 1.0)

        ratio = 0.6 + 0.3 * (1.0 - eb)
        # Guard against floating-point drift outside the expected band.
        if ratio < 0.0:
            ratio = 0.0
        if ratio > 1.0:
            ratio = 1.0
        compressed_size = int(source_size * ratio)

        if ratio > 0.85:
            status = CompressionStatus.UNCOMPRESSED
        elif ratio > 0.7:
            status = CompressionStatus.PARTIAL
        elif ratio > 0.5:
            status = CompressionStatus.COMPRESSED
        else:
            status = CompressionStatus.LOSSY

        entropy_after = eb * ratio
        if status == CompressionStatus.LOSSY:
            information_loss = max(0.0, eb * (1.0 - ratio))
        else:
            information_loss = 0.0

        with self._lock:
            trace = CompressionTrace(
                agent_id=agent_id,
                source_payload_size=source_size,
                compressed_size=compressed_size,
                ratio=ratio,
                status=status,
                entropy_before=eb,
                entropy_after=entropy_after,
                information_loss=information_loss,
            )
            self._compressions[trace.trace_id] = trace
            self._stats["total_compressions"] += 1
            return trace

    def get_compression(self, trace_id: str) -> Optional[CompressionTrace]:
        """Retrieve a compression trace by id, or ``None`` if absent."""
        with self._lock:
            return self._compressions.get(trace_id)

    def list_compressions(
        self,
        agent_id: Optional[str] = None,
        status: Optional[Any] = None,
    ) -> List[CompressionTrace]:
        """Return compression traces, optionally filtered.

        Filters by ``agent_id`` and ``status``; either filter left as
        ``None`` matches all values for that field. ``status`` may be
        passed as a ``CompressionStatus`` or its string name/value. The
        returned list is a snapshot copy.
        """
        with self._lock:
            traces = list(self._compressions.values())
        if agent_id is not None:
            traces = [t for t in traces if t.agent_id == agent_id]
        if status is not None:
            status_enum = _resolve_enum(CompressionStatus, status)
            traces = [t for t in traces if t.status == status_enum]
        return traces

    # ── Profiles ───────────────────────────────────────────────────

    def get_or_create_profile(self, agent_id: str) -> EntropyProfile:
        """Get the entropy profile for ``agent_id``, creating it if absent.

        A fresh profile starts in the BALANCED regime with zero averages,
        zero volatility, zero samples, and empty (zero-initialized)
        regime and kind distributions. Subsequent calls return the same
        profile object.
        """
        with self._lock:
            profile = self._profiles.get(agent_id)
            if profile is None:
                profile = EntropyProfile(agent_id=agent_id)
                self._profiles[agent_id] = profile
            return profile

    def update_profile(self, agent_id: str, **kwargs: Any) -> EntropyProfile:
        """Update fields on an agent's entropy profile.

        Accepts keyword arguments matching ``EntropyProfile`` field names:
        ``regime`` (an ``EntropyRegime`` or its string name/value),
        ``avg_entropy``, ``avg_normalized``, ``flux_volatility``,
        ``samples_count``, ``regime_distribution``, and
        ``kind_distribution``. Unknown keys are ignored. The profile's
        ``updated_at`` timestamp is refreshed. The profile is created on
        the fly if it does not yet exist.
        """
        with self._lock:
            profile = self.get_or_create_profile(agent_id)
            if "regime" in kwargs:
                profile.regime = _resolve_enum(EntropyRegime, kwargs["regime"])
            for key in (
                "avg_entropy",
                "avg_normalized",
                "flux_volatility",
                "samples_count",
            ):
                if key in kwargs:
                    setattr(profile, key, kwargs[key])
            if "regime_distribution" in kwargs:
                profile.regime_distribution = dict(kwargs["regime_distribution"])
            if "kind_distribution" in kwargs:
                profile.kind_distribution = dict(kwargs["kind_distribution"])
            profile.updated_at = _now()
            return profile

    def list_profiles(self) -> List[EntropyProfile]:
        """Return all entropy profiles currently registered.

        The returned list is a snapshot copy; mutating it does not affect
        the engine.
        """
        with self._lock:
            return list(self._profiles.values())

    # ── Statistics ─────────────────────────────────────────────────

    def get_stats(self) -> EntropyStats:
        """Compute aggregate statistics over the current engine state.

        Totals are read from the running counters (kept in sync with the
        registries). ``avg_shannon_entropy`` and ``avg_normalized_entropy``
        are computed live across all samples (zero when there are no
        samples). ``regime_distribution`` tallies each sample by the
        regime implied by its normalized entropy. ``flux_direction_distribution``
        tallies each flux record by its direction. The breakdown dicts
        are fully populated with a zero entry for every enum member so
        callers can rely on key presence.
        """
        with self._lock:
            samples = list(self._samples.values())
            flux_records = list(self._flux_records.values())

            regime_dist = _empty_regime_distribution()
            for sample in samples:
                regime = _determine_regime(sample.normalized_entropy)
                regime_dist[regime] += 1

            direction_dist = _empty_flux_direction_distribution()
            for record in flux_records:
                direction_dist[record.direction] += 1

            if samples:
                avg_shannon = sum(s.shannon_entropy for s in samples) / len(samples)
                avg_norm = sum(s.normalized_entropy for s in samples) / len(samples)
            else:
                avg_shannon = 0.0
                avg_norm = 0.0

            return EntropyStats(
                total_samples=self._stats["total_samples"],
                total_flux_records=self._stats["total_flux_records"],
                total_inferences=self._stats["total_inferences"],
                total_compressions=self._stats["total_compressions"],
                avg_shannon_entropy=avg_shannon,
                avg_normalized_entropy=avg_norm,
                regime_distribution=regime_dist,
                flux_direction_distribution=direction_dist,
            )

    # ── Maintenance ─────────────────────────────────────────────────

    def reset(self) -> None:
        """Clear all engine state. Intended for tests.

        Empties every registry, resets the running counters, and drops all
        per-agent flux tracking state. After reset the engine behaves as
        if freshly constructed.
        """
        with self._lock:
            self._samples.clear()
            self._flux_records.clear()
            self._inferences.clear()
            self._compressions.clear()
            self._profiles.clear()
            self._stats.clear()
            self._stats.update(
                {
                    "total_samples": 0,
                    "total_flux_records": 0,
                    "total_inferences": 0,
                    "total_compressions": 0,
                }
            )
            self._last_entropy.clear()
            self._last_flux_time.clear()
            self._flux_delta_history.clear()


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine = None
_engine_lock = threading.Lock()


def get_entropy_engine() -> AgentCognitiveEntropy:
    """Get or create the singleton ``AgentCognitiveEntropy`` instance.

    The first call constructs the engine; subsequent calls return the same
    instance. Access is guarded by a module-level lock so the singleton is
    safe to initialize from multiple threads.
    """
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = AgentCognitiveEntropy()
        return _engine


def reset_entropy_engine() -> None:
    """Reset the singleton ``AgentCognitiveEntropy`` instance.

    Clears any state held by the current engine (if one exists) and drops
    the reference so the next ``get_entropy_engine`` call creates a fresh
    instance. Useful for tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        if _engine is not None:
            _engine.reset()
        _engine = None
