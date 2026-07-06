from __future__ import annotations

"""Agent Cognitive Symbology Engine — symbolic representation layer of cognition

Concepts must be encoded as symbols before they can be substituted, combined,
or transformed. The engine tracks sign types, encoding outcomes, and operations.

Core capabilities:
  - Symbol Encoding: concepts encoded as icons, indices, tokens, metaphors, etc.
  - Symbolic Operations: substitute, combine, decompose, abstract, instantiate, transform
  - Encoding Outcomes: redundant, ambiguous, partial, failed, succeeded
  - Density Classification: barren, sparse, moderate, dense, saturated
  - Transformation Regime: dormant, occasional, active, fluid, turbulent
Architecture:
  AgentCognitiveSymbology (singleton)
  ├── SymbolEntry, SymbolicAction           (encoded symbols, operations)
  ├── EncodingAttempt, SymbologySnapshot    (encoding outcomes, aggregate state)
  ├── TransformationTrace, SymbologyProfile (multi-step traces, per-agent)
  └── SymbologyStats                        (engine-wide statistics)
"""

import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _now() -> str:
    """Return an ISO-8601 UTC timestamp string."""
    return datetime.utcnow().isoformat()


def _new_id() -> str:
    """Generate a short unique identifier for a symbol/action/snapshot/etc."""
    return str(uuid.uuid4())[:8]


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a numeric value into the inclusive range [low, high].

    Non-numeric input is coerced to ``low`` so callers cannot poison the
    engine with a ``NaN`` or ``None`` density contribution.
    """
    try:
        f = float(value)
    except (TypeError, ValueError):
        f = low
    if f < low:
        return low
    if f > high:
        return high
    return f


def _resolve_enum(enum_cls: type, value: Any) -> Any:
    """Resolve a value to an enum member, accepting name or value strings.

    Enum members are returned unchanged. Strings are matched first against
    member values (e.g. ``"icon"``) and then against member names
    (e.g. ``"ICON"``), so callers may pass either form. Raises
    ``ValueError`` if neither matches.
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


def _enum_value(enum_cls: type, value: Any) -> str:
    """Return the ``.value`` of an enum member, or a string fallback.

    Used inside ``to_dict`` methods so a stored field always serializes to
    a plain string even if a non-enum slipped in through direct
    construction.
    """
    if isinstance(value, enum_cls):
        return value.value
    return str(value)


def _determine_density(
    symbol_count: int, avg_contribution: float = 0.0
) -> "SymbolicDensity":
    """Classify an agent's symbolic density from its symbol count.

    The bands partition the non-negative integers into five qualitative
    regimes. ``avg_contribution`` is accepted so callers can pass the
    agent's mean density contribution alongside the count, but the
    classification is count-driven: a BARREN layer has no symbols at all,
    a SPARSE layer has fewer than ten, MODERATE has fewer than thirty,
    DENSE has fewer than sixty, and anything at or above sixty is
    SATURATED (over-symbolized). The contribution average is preserved in
    the signature for callers that want to record it on the snapshot
    without recomputing.
    """
    try:
        count = int(symbol_count)
    except (TypeError, ValueError):
        count = 0
    if count < 0:
        count = 0
    if count == 0:
        return SymbolicDensity.BARREN
    if count < 10:
        return SymbolicDensity.SPARSE
    if count < 30:
        return SymbolicDensity.MODERATE
    if count < 60:
        return SymbolicDensity.DENSE
    return SymbolicDensity.SATURATED


def _determine_regime(operation_count: int) -> "TransformationRegime":
    """Classify the transformation regime from the number of operations.

    The bands describe the tempo and character of symbolic manipulation.
    Zero operations means DORMANT — the symbolic layer is static. Few
    operations mean OCCASIONAL transformation. A regular cadence means
    ACTIVE, the healthy working tempo. A higher but still coherent
    cadence means FLUID — symbolic manipulation is frequent and smooth.
    Beyond that, the cadence becomes TURBULENT: transformations are
    happening so fast that they risk incoherence.
    """
    try:
        count = int(operation_count)
    except (TypeError, ValueError):
        count = 0
    if count < 0:
        count = 0
    if count == 0:
        return TransformationRegime.DORMANT
    if count < 5:
        return TransformationRegime.OCCASIONAL
    if count < 15:
        return TransformationRegime.ACTIVE
    if count < 40:
        return TransformationRegime.FLUID
    return TransformationRegime.TURBULENT


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class SymbolType(str, Enum):
    """The form a symbol takes, classified by its relation to its referent.

    The classical semiotic tradition distinguishes signs by the
    relationship they bear to what they stand for. The engine tracks that
    form because the kind of symbol determines what operations are
    meaningful on it: icons can be inspected for resemblance, tokens can
    only be combined by convention, metaphors can be decomposed into
    their source and target domains.

    ICON resembles its referent — the sign carries structural similarity
    to what it stands for, like a diagram or a map. INDEX is causally
    linked to its referent — the sign is produced by its referent, like
    smoke indexing fire. TOKEN is an arbitrary conventional sign — the
    sign stands for its referent by agreement alone, like a word.
    METAPHOR maps structure from another domain — the sign borrows a
    foreign structure to stand for its referent, like "branch" of
    government. METONYM is associated by contiguity — the sign stands for
    its referent through adjacency, like the crown for the monarchy.
    ABSTRACT is a pure abstraction — the sign's referent is itself an
    abstraction with no concrete anchor, like a variable in algebra.
    """
    ICON = "icon"            # resembles referent
    INDEX = "index"          # causally linked to referent
    TOKEN = "token"          # arbitrary conventional sign
    METAPHOR = "metaphor"    # mapping from another domain
    METONYM = "metonym"      # associated by contiguity
    ABSTRACT = "abstract"    # pure abstraction


class SymbolicOperation(str, Enum):
    """The operations the engine can perform on symbols.

    A symbolic operation is a transformation applied to one or more
    symbols to produce one or more symbols. Each operation is a distinct
    move in the algebra of sign manipulation.

    SUBSTITUTE replaces one symbol with another — the basic move of
    algebraic and logical manipulation. COMBINE merges two or more
    symbols into a new compound symbol, building complex representations
    from simple ones. DECOMPOSE breaks a compound symbol into its
    sub-symbols, exposing internal structure. ABSTRACT moves a symbol to
    a more abstract form, climbing from instance to category.
    INSTANTIATE moves a symbol to a concrete instance, descending from
    category to instance. TRANSFORM changes a symbol from one type to
    another, reshaping the agent's own sign system.
    """
    SUBSTITUTE = "substitute"    # replace one symbol with another
    COMBINE = "combine"          # merge symbols
    DECOMPOSE = "decompose"      # break into sub-symbols
    ABSTRACT = "abstract"        # move to more abstract symbol
    INSTANTIATE = "instantiate"  # move to concrete instance
    TRANSFORM = "transform"      # change symbol type


class SymbolicDensity(str, Enum):
    """The density of an agent's symbolic layer.

    Density classifies how richly the agent has encoded its conceptual
    content into manipulable symbols. Neither extreme is unconditionally
    desirable: a BARREN layer means the agent has concepts but has not
    encoded them, so it cannot manipulate them; a SATURATED layer means
    the agent has over-symbolized, and the surplus symbols add noise
    rather than capacity. The healthy working range sits between SPARSE
    and DENSE.

    BARREN means no symbols at all — the agent has concepts but has not
    encoded any of them into symbolic form. SPARSE means few symbols,
    inadequate coverage. MODERATE means adequate symbol coverage for
    routine reasoning. DENSE means a rich symbolic layer, where
    manipulation is most powerful. SATURATED means over-symbolized — the
    agent has encoded more than it can usefully manipulate.
    """
    BARREN = "barren"        # no symbols
    SPARSE = "sparse"        # few symbols
    MODERATE = "moderate"    # adequate symbol coverage
    DENSE = "dense"          # rich symbolic layer
    SATURATED = "saturated"  # over-symbolized


class EncodingOutcome(str, Enum):
    """The outcome of an attempt to encode a concept as a symbol.

    Not every encoding succeeds cleanly. The outcome records what
    happened when the agent tried to encode a concept into a symbol of a
    given type, so the agent can inspect where its symbolic layer is
    well-formed and where it is leaky.

    SUCCESS means the concept was encoded cleanly as a symbol of the
    requested type. PARTIAL means the concept was encoded but some of its
    content did not make it into the symbol. AMBIGUOUS means the concept
    admitted multiple encodings and the engine could not settle on one.
    FAILED means the concept resisted encoding in the requested form.
    REDUNDANT means the concept already had a symbol of that type, so
    re-encoding added nothing.
    """
    SUCCESS = "success"      # encoding succeeded
    PARTIAL = "partial"      # partially encoded
    AMBIGUOUS = "ambiguous"  # multiple encodings possible
    FAILED = "failed"        # could not encode
    REDUNDANT = "redundant"  # already encoded


class TransformationRegime(str, Enum):
    """The tempo and character of an agent's symbolic transformations.

    A regime classifies how the agent is operating on its symbols over
    time. The healthy working tempo is ACTIVE or FLUID; DORMANT signals a
    static layer, and TURBULENT signals a layer being reshuffled faster
    than it can be grounded.

    DORMANT means no transformations are occurring — the symbolic layer is
    static. OCCASIONAL means transformations are infrequent.
    ACTIVE means transformations occur regularly, the healthy working
    tempo. FLUID means transformations are frequent and smooth, the
    regime where symbolic manipulation is most productive.
    TURBULENT means the transformations are chaotic: too many, too fast,
    without coherence.
    """
    DORMANT = "dormant"        # no transformations
    OCCASIONAL = "occasional"  # infrequent
    ACTIVE = "active"          # regular
    FLUID = "fluid"            # frequent and smooth
    TURBULENT = "turbulent"    # chaotic transformations


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class SymbolEntry:
    """One symbol encoded by an agent.

    A symbol is a concept encoded in a form that can be manipulated,
    combined, and transformed. ``symbol_id`` uniquely identifies this
    symbol. ``agent_id`` is the agent that encoded it. ``label`` is the
    human-readable name of the symbol (e.g. ``"branch-of-government"``).
    ``symbol_type`` is the ``SymbolType`` describing the form the symbol
    takes — icon, index, token, metaphor, metonym, or abstract.
    ``referent`` is a human-readable description of what the symbol stands
    for. ``encoding`` is the encoded form itself — the string or
    representation that carries the meaning. ``density_contribution`` in
    [0, 1] is how much this symbol contributes to the density of the
    agent's symbolic layer, where 0 means a negligible contribution and 1
    means a fully weighted symbol. ``timestamp`` is when the symbol was
    registered.
    """
    symbol_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    label: str = ""
    symbol_type: SymbolType = SymbolType.TOKEN
    referent: str = ""
    encoding: str = ""
    density_contribution: float = 0.0
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this symbol to a plain dict, expanding the enum."""
        return {
            "symbol_id": self.symbol_id,
            "agent_id": self.agent_id,
            "label": self.label,
            "symbol_type": _enum_value(SymbolType, self.symbol_type),
            "referent": self.referent,
            "encoding": self.encoding,
            "density_contribution": self.density_contribution,
            "timestamp": self.timestamp,
        }


@dataclass
class SymbolicAction:
    """One symbolic operation performed by an agent.

    Records a single application of a ``SymbolicOperation`` to a set of
    input symbols, producing a set of output symbols. ``action_id``
    uniquely identifies this action. ``agent_id`` is the agent that
    performed it. ``operation`` is the ``SymbolicOperation`` applied
    (substitute, combine, decompose, abstract, instantiate, transform).
    ``input_symbols`` is the list of symbol labels that were the inputs.
    ``output_symbols`` is the list of symbol labels that were produced.
    ``rationale`` is a free-form explanation of why the operation was
    performed. ``timestamp`` is when the action was recorded.
    """
    action_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    operation: SymbolicOperation = SymbolicOperation.COMBINE
    input_symbols: List[str] = field(default_factory=list)
    output_symbols: List[str] = field(default_factory=list)
    rationale: str = ""
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this action to a plain dict, expanding the enum."""
        return {
            "action_id": self.action_id,
            "agent_id": self.agent_id,
            "operation": _enum_value(SymbolicOperation, self.operation),
            "input_symbols": list(self.input_symbols),
            "output_symbols": list(self.output_symbols),
            "rationale": self.rationale,
            "timestamp": self.timestamp,
        }


@dataclass
class EncodingAttempt:
    """One attempt to encode a concept as a symbol.

    ``attempt_id`` uniquely identifies this attempt. ``agent_id`` is the
    agent that attempted the encoding. ``concept`` is the concept the
    agent tried to encode. ``symbol_type`` is the ``SymbolType`` the
    agent tried to encode the concept as. ``outcome`` is the
    ``EncodingOutcome`` of the attempt — success, partial, ambiguous,
    failed, or redundant. ``encoded_symbol`` is the symbol label produced
    on a successful or partial encoding, or ``None`` when the encoding
    failed or was redundant. ``timestamp`` is when the attempt was made.
    """
    attempt_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    concept: str = ""
    symbol_type: SymbolType = SymbolType.TOKEN
    outcome: EncodingOutcome = EncodingOutcome.SUCCESS
    encoded_symbol: Optional[str] = None
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this attempt to a plain dict, expanding the enums.

        ``encoded_symbol`` is emitted as ``None`` when unset, or as the
        stored string when set, so the serialized form is JSON-friendly.
        """
        return {
            "attempt_id": self.attempt_id,
            "agent_id": self.agent_id,
            "concept": self.concept,
            "symbol_type": _enum_value(SymbolType, self.symbol_type),
            "outcome": _enum_value(EncodingOutcome, self.outcome),
            "encoded_symbol": self.encoded_symbol,
            "timestamp": self.timestamp,
        }


@dataclass
class SymbologySnapshot:
    """A point-in-time aggregate of an agent's symbolic layer.

    A snapshot summarizes the agent's symbols and actions at the moment
    it was taken. ``snapshot_id`` uniquely identifies this snapshot.
    ``agent_id`` is the agent the snapshot summarizes. ``density`` is the
    ``SymbolicDensity`` derived from the agent's symbol count via
    ``_determine_density``. ``regime`` is the ``TransformationRegime``
    derived from the agent's action count via ``_determine_regime``.
    ``total_symbols`` is the count of symbols registered for the agent at
    snapshot time. ``total_operations`` is the count of actions recorded
    for the agent at snapshot time. ``dominant_type`` is the most common
    ``SymbolType`` among the agent's symbols, or ``None`` when the agent
    has no symbols. ``timestamp`` is when the snapshot was taken.
    """
    snapshot_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    density: SymbolicDensity = SymbolicDensity.BARREN
    regime: TransformationRegime = TransformationRegime.DORMANT
    total_symbols: int = 0
    total_operations: int = 0
    dominant_type: Optional[SymbolType] = None
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a plain dict, expanding the enums.

        ``dominant_type`` may be ``None``; it is serialized as ``None`` in
        that case rather than as a string.
        """
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "density": _enum_value(SymbolicDensity, self.density),
            "regime": _enum_value(TransformationRegime, self.regime),
            "total_symbols": self.total_symbols,
            "total_operations": self.total_operations,
            "dominant_type": (
                _enum_value(SymbolType, self.dominant_type)
                if self.dominant_type is not None
                else None
            ),
            "timestamp": self.timestamp,
        }


@dataclass
class TransformationTrace:
    """A record of a multi-step symbolic transformation.

    A trace records the sequence of steps by which one symbol was
    transformed into another, capturing the path of a transformation
    that cannot be expressed as a single operation. ``trace_id`` uniquely
    identifies this trace. ``agent_id`` is the agent that performed the
    transformation. ``from_symbol`` is the label of the source symbol.
    ``to_symbol`` is the label of the target symbol. ``operation`` is the
    ``SymbolicOperation`` that classifies the overall transformation.
    ``steps`` is the ordered list of human-readable step descriptions
    that compose the transformation. ``timestamp`` is when the trace was
    recorded.
    """
    trace_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    from_symbol: str = ""
    to_symbol: str = ""
    operation: SymbolicOperation = SymbolicOperation.TRANSFORM
    steps: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this trace to a plain dict, expanding the enum."""
        return {
            "trace_id": self.trace_id,
            "agent_id": self.agent_id,
            "from_symbol": self.from_symbol,
            "to_symbol": self.to_symbol,
            "operation": _enum_value(SymbolicOperation, self.operation),
            "steps": list(self.steps),
            "timestamp": self.timestamp,
        }


@dataclass
class SymbologyProfile:
    """Per-agent aggregate symbology posture.

    A profile summarizes one agent's symbolic layer. ``agent_id`` is the
    agent this profile describes. ``total_symbols`` is the count of
    symbols registered for the agent. ``avg_density`` in [0, 1] is the
    mean density contribution across the agent's symbols (zero when there
    are none). ``dominant_type`` is the most common ``SymbolType`` among
    the agent's symbols, or ``None`` when there are no symbols.
    ``regime`` is the ``TransformationRegime`` derived from the agent's
    action count. ``total_encodings`` is the count of encoding attempts
    recorded for the agent. ``total_operations`` is the count of actions
    recorded for the agent. ``last_updated`` records when the profile was
    last refreshed.
    """
    agent_id: str = ""
    total_symbols: int = 0
    avg_density: float = 0.0
    dominant_type: Optional[SymbolType] = None
    regime: TransformationRegime = TransformationRegime.DORMANT
    total_encodings: int = 0
    total_operations: int = 0
    last_updated: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict, expanding the enums.

        ``dominant_type`` may be ``None``; it is serialized as ``None`` in
        that case rather than as a string.
        """
        return {
            "agent_id": self.agent_id,
            "total_symbols": self.total_symbols,
            "avg_density": self.avg_density,
            "dominant_type": (
                _enum_value(SymbolType, self.dominant_type)
                if self.dominant_type is not None
                else None
            ),
            "regime": _enum_value(TransformationRegime, self.regime),
            "total_encodings": self.total_encodings,
            "total_operations": self.total_operations,
            "last_updated": self.last_updated,
        }


@dataclass
class SymbologyStats:
    """Engine-wide aggregate statistics.

    Counts of symbols, actions, encoding attempts, snapshots, and traces
    across all agents. ``density_distribution`` tallies all snapshots by
    their density. ``type_distribution`` tallies all symbols by their
    symbol type. ``operation_distribution`` tallies all actions by their
    operation. The breakdown dicts are keyed by enum ``.value`` strings
    so the stats serialize cleanly to JSON.
    """
    total_symbols: int = 0
    total_actions: int = 0
    total_encodings: int = 0
    total_snapshots: int = 0
    total_traces: int = 0
    density_distribution: Dict[str, int] = field(default_factory=dict)
    type_distribution: Dict[str, int] = field(default_factory=dict)
    operation_distribution: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict.

        The breakdown dicts are shallow-copied so the serialized form is
        independent of the live stats.
        """
        return {
            "total_symbols": self.total_symbols,
            "total_actions": self.total_actions,
            "total_encodings": self.total_encodings,
            "total_snapshots": self.total_snapshots,
            "total_traces": self.total_traces,
            "density_distribution": dict(self.density_distribution),
            "type_distribution": dict(self.type_distribution),
            "operation_distribution": dict(self.operation_distribution),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveSymbology:
    """Thread-safe engine managing the symbolic representation layer of cognition.

    Holds symbols, symbolic actions, encoding attempts, snapshots,
    transformation traces, and per-agent profiles. A symbol is a concept
    encoded in a form that can be manipulated; the engine records each
    symbol with its type, referent, encoding, and density contribution.
    A symbolic action records one application of a symbolic operation
    (substitute, combine, decompose, abstract, instantiate, transform) to
    a set of input symbols producing a set of output symbols. An encoding
    attempt records one attempt to encode a concept as a symbol, with the
    outcome of that attempt. A snapshot aggregates an agent's symbolic
    layer at a point in time into a density, a regime, a symbol count, an
    operation count, and a dominant symbol type. A transformation trace
    records the multi-step path by which one symbol became another.

    All state mutations are guarded by a single reentrant lock so the
    engine is safe to call from multiple threads. The reentrant lock
    allows public methods to delegate to one another (for example,
    ``update_profile`` calls ``get_profile``) without self-deadlock. The
    engine is intentionally dependency-free so it can run in any Buddy
    runtime without extra packages.

    The engine is a measurement instrument first and a control system
    second. It records how the agent's concepts are encoded as symbols and
    how those symbols are transformed, classifies the density and regime
    of the resulting symbolic layer, and makes that state legible so the
    agent (or its orchestrator) can decide whether its symbolic layer is
    adequately populated and coherently worked.
    """

    # Caps to keep the in-memory engine bounded under runaway callers.
    MAX_SYMBOLS: int = 5000
    MAX_ACTIONS: int = 5000
    MAX_ENCODINGS: int = 5000
    MAX_SNAPSHOTS: int = 5000
    MAX_TRACES: int = 5000
    # Default list size cap applied when a list method is called without
    # an explicit limit.
    DEFAULT_LIST_LIMIT: int = 50

    def __init__(self) -> None:
        self._symbols: Dict[str, SymbolEntry] = {}
        self._actions: Dict[str, SymbolicAction] = {}
        self._encodings: Dict[str, EncodingAttempt] = {}
        self._snapshots: Dict[str, SymbologySnapshot] = {}
        self._traces: Dict[str, TransformationTrace] = {}
        self._profiles: Dict[str, SymbologyProfile] = {}
        # Running integer counters, kept in sync with the registries above.
        self._stats: Dict[str, int] = {
            "total_symbols": 0,
            "total_actions": 0,
            "total_encodings": 0,
            "total_snapshots": 0,
            "total_traces": 0,
        }
        # Reentrant lock so public methods may call one another safely.
        self._lock: threading.RLock = threading.RLock()
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    # ── Internal Helpers ──────────────────────────────────────────

    def _agent_symbols(self, agent_id: str) -> List[SymbolEntry]:
        """Return this agent's symbols in insertion order (no lock)."""
        return [s for s in self._symbols.values() if s.agent_id == agent_id]

    def _agent_actions(self, agent_id: str) -> List[SymbolicAction]:
        """Return this agent's actions in insertion order (no lock)."""
        return [a for a in self._actions.values() if a.agent_id == agent_id]

    def _agent_encodings(self, agent_id: str) -> List[EncodingAttempt]:
        """Return this agent's encoding attempts in insertion order (no lock)."""
        return [e for e in self._encodings.values() if e.agent_id == agent_id]

    @staticmethod
    def _dominant_type(symbols: List[SymbolEntry]) -> Optional[SymbolType]:
        """Return the most common ``SymbolType`` among the given symbols.

        Returns ``None`` when the list is empty. Ties are broken by first
        occurrence in iteration order over the input list.
        """
        if not symbols:
            return None
        counts: Dict[SymbolType, int] = {}
        for s in symbols:
            counts[s.symbol_type] = counts.get(s.symbol_type, 0) + 1
        return max(counts.items(), key=lambda kv: kv[1])[0]

    def _concept_has_symbol_of_type(
        self, agent_id: str, concept: str, symbol_type: SymbolType
    ) -> bool:
        """Return whether the agent already has a symbol of the given type.

        A concept is considered already encoded as a symbol of the given
        type when the agent has a registered symbol whose ``label`` or
        ``referent`` matches the concept and whose ``symbol_type`` matches
        the requested type. The match is case-sensitive.
        """
        for s in self._symbols.values():
            if s.agent_id != agent_id:
                continue
            if s.symbol_type != symbol_type:
                continue
            if s.label == concept or s.referent == concept:
                return True
        return False

    # ── Symbols ──────────────────────────────────────────────────

    def register_symbol(
        self,
        agent_id: str,
        label: str,
        symbol_type: Any,
        referent: str,
        encoding: str,
        density_contribution: float,
    ) -> SymbolEntry:
        """Register a symbol for an agent and return it.

        ``symbol_type`` accepts a ``SymbolType`` member or its value/name
        string. ``density_contribution`` in [0, 1] is clamped to that
        range; it expresses how much this symbol contributes to the
        density of the agent's symbolic layer. ``referent`` is a
        human-readable description of what the symbol stands for, and
        ``encoding`` is the encoded form that carries the meaning. Raises
        ``RuntimeError`` if the symbol registry is full.
        """
        with self._lock:
            if len(self._symbols) >= self.MAX_SYMBOLS:
                raise RuntimeError("symbol registry is full")
            symbol = SymbolEntry(
                agent_id=agent_id,
                label=str(label),
                symbol_type=_resolve_enum(SymbolType, symbol_type),
                referent=str(referent),
                encoding=str(encoding),
                density_contribution=_clamp(density_contribution, 0.0, 1.0),
                timestamp=_now(),
            )
            self._symbols[symbol.symbol_id] = symbol
            self._stats["total_symbols"] += 1
            return symbol

    def list_symbols(
        self,
        agent_id: Optional[str] = None,
        limit: int = DEFAULT_LIST_LIMIT,
    ) -> List[SymbolEntry]:
        """Return symbols, optionally filtered by agent, capped to ``limit``.

        ``agent_id`` filters to symbols registered for that agent.
        ``limit`` caps the number of results, applied after filtering.
        The returned list is ordered most-recent-last (insertion order)
        and is a snapshot copy; mutating it does not affect the engine.
        """
        with self._lock:
            symbols = list(self._symbols.values())
        if agent_id is not None:
            symbols = [s for s in symbols if s.agent_id == agent_id]
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = self.DEFAULT_LIST_LIMIT
        if n < 0:
            n = 0
        return symbols[-n:] if n else []

    def get_symbol(self, symbol_id: str) -> Optional[SymbolEntry]:
        """Retrieve a symbol by id, or ``None`` if absent."""
        with self._lock:
            return self._symbols.get(symbol_id)

    # ── Symbolic Actions ─────────────────────────────────────────

    def perform_action(
        self,
        agent_id: str,
        operation: Any,
        input_symbols: List[str],
        output_symbols: List[str],
        rationale: str,
    ) -> SymbolicAction:
        """Record a symbolic action for an agent and return it.

        ``operation`` accepts a ``SymbolicOperation`` member or its
        value/name string. ``input_symbols`` is the list of symbol labels
        that were the inputs to the operation. ``output_symbols`` is the
        list of symbol labels that were produced. ``rationale`` is a
        free-form explanation of why the operation was performed. Raises
        ``RuntimeError`` if the action registry is full.
        """
        with self._lock:
            if len(self._actions) >= self.MAX_ACTIONS:
                raise RuntimeError("action registry is full")
            action = SymbolicAction(
                agent_id=agent_id,
                operation=_resolve_enum(SymbolicOperation, operation),
                input_symbols=[str(s) for s in (input_symbols or [])],
                output_symbols=[str(s) for s in (output_symbols or [])],
                rationale=str(rationale),
                timestamp=_now(),
            )
            self._actions[action.action_id] = action
            self._stats["total_actions"] += 1
            return action

    def list_actions(
        self,
        agent_id: Optional[str] = None,
        limit: int = DEFAULT_LIST_LIMIT,
    ) -> List[SymbolicAction]:
        """Return actions, optionally filtered by agent, capped to ``limit``.

        ``agent_id`` filters to actions recorded for that agent.
        ``limit`` caps the number of results, applied after filtering.
        The returned list is ordered most-recent-last (insertion order)
        and is a snapshot copy; mutating it does not affect the engine.
        """
        with self._lock:
            actions = list(self._actions.values())
        if agent_id is not None:
            actions = [a for a in actions if a.agent_id == agent_id]
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = self.DEFAULT_LIST_LIMIT
        if n < 0:
            n = 0
        return actions[-n:] if n else []

    def get_action(self, action_id: str) -> Optional[SymbolicAction]:
        """Retrieve an action by id, or ``None`` if absent."""
        with self._lock:
            return self._actions.get(action_id)

    # ── Encoding Attempts ────────────────────────────────────────

    def attempt_encoding(
        self,
        agent_id: str,
        concept: str,
        symbol_type: Any,
    ) -> EncodingAttempt:
        """Attempt to encode a concept as a symbol and return the attempt.

        ``symbol_type`` accepts a ``SymbolType`` member or its value/name
        string. The outcome is determined by whether the concept already
        has a symbol of the requested type registered for the agent:
        when it does, the outcome is ``REDUNDANT`` and no new symbol is
        produced (``encoded_symbol`` is ``None``); when it does not, the
        encoding ``SUCCESS`` and ``encoded_symbol`` is set to the concept
        label, representing the freshly encoded symbol. Raises
        ``RuntimeError`` if the encoding registry is full.
        """
        member_type = _resolve_enum(SymbolType, symbol_type)
        with self._lock:
            if len(self._encodings) >= self.MAX_ENCODINGS:
                raise RuntimeError("encoding registry is full")
            already_encoded = self._concept_has_symbol_of_type(
                agent_id, str(concept), member_type
            )
            if already_encoded:
                outcome = EncodingOutcome.REDUNDANT
                encoded_symbol: Optional[str] = None
            else:
                outcome = EncodingOutcome.SUCCESS
                encoded_symbol = str(concept)
            attempt = EncodingAttempt(
                agent_id=agent_id,
                concept=str(concept),
                symbol_type=member_type,
                outcome=outcome,
                encoded_symbol=encoded_symbol,
                timestamp=_now(),
            )
            self._encodings[attempt.attempt_id] = attempt
            self._stats["total_encodings"] += 1
            return attempt

    def list_encodings(
        self,
        agent_id: Optional[str] = None,
        limit: int = DEFAULT_LIST_LIMIT,
    ) -> List[EncodingAttempt]:
        """Return encoding attempts, optionally filtered by agent, capped to ``limit``.

        ``agent_id`` filters to attempts recorded for that agent.
        ``limit`` caps the number of results, applied after filtering.
        The returned list is ordered most-recent-last (insertion order)
        and is a snapshot copy; mutating it does not affect the engine.
        """
        with self._lock:
            encodings = list(self._encodings.values())
        if agent_id is not None:
            encodings = [e for e in encodings if e.agent_id == agent_id]
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = self.DEFAULT_LIST_LIMIT
        if n < 0:
            n = 0
        return encodings[-n:] if n else []

    def get_encoding(self, attempt_id: str) -> Optional[EncodingAttempt]:
        """Retrieve an encoding attempt by id, or ``None`` if absent."""
        with self._lock:
            return self._encodings.get(attempt_id)

    # ── Snapshots ─────────────────────────────────────────────────

    def take_snapshot(self, agent_id: str) -> SymbologySnapshot:
        """Aggregate an agent's symbolic layer into a snapshot.

        ``total_symbols`` is the count of symbols registered for the
        agent. ``total_operations`` is the count of actions recorded for
        the agent. ``density`` is derived from the symbol count via
        ``_determine_density``. ``regime`` is derived from the action
        count via ``_determine_regime``. ``dominant_type`` is the most
        common ``SymbolType`` among the agent's symbols, or ``None`` when
        the agent has no symbols. The snapshot is stored in the engine
        and reflected in the engine stats. If the agent has no symbols,
        ``density`` is ``BARREN`` and ``dominant_type`` is ``None``; if
        the agent has no actions, ``regime`` is ``DORMANT``.
        """
        with self._lock:
            agent_symbols = self._agent_symbols(agent_id)
            agent_actions = self._agent_actions(agent_id)
            total_symbols = len(agent_symbols)
            total_operations = len(agent_actions)
            density = _determine_density(total_symbols)
            regime = _determine_regime(total_operations)
            dominant_type = self._dominant_type(agent_symbols)
            snapshot = SymbologySnapshot(
                agent_id=agent_id,
                density=density,
                regime=regime,
                total_symbols=total_symbols,
                total_operations=total_operations,
                dominant_type=dominant_type,
                timestamp=_now(),
            )
            self._snapshots[snapshot.snapshot_id] = snapshot
            self._stats["total_snapshots"] += 1
            return snapshot

    def list_snapshots(
        self,
        agent_id: Optional[str] = None,
        limit: int = DEFAULT_LIST_LIMIT,
    ) -> List[SymbologySnapshot]:
        """Return snapshots, optionally filtered by agent, capped to ``limit``.

        ``agent_id`` filters to snapshots taken for that agent. ``limit``
        caps the number of results, applied after filtering. The returned
        list is ordered most-recent-last (insertion order) and is a
        snapshot copy; mutating it does not affect the engine.
        """
        with self._lock:
            snapshots = list(self._snapshots.values())
        if agent_id is not None:
            snapshots = [s for s in snapshots if s.agent_id == agent_id]
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = self.DEFAULT_LIST_LIMIT
        if n < 0:
            n = 0
        return snapshots[-n:] if n else []

    def get_snapshot(self, snapshot_id: str) -> Optional[SymbologySnapshot]:
        """Retrieve a snapshot by id, or ``None`` if absent."""
        with self._lock:
            return self._snapshots.get(snapshot_id)

    # ── Transformation Traces ────────────────────────────────────

    def trace_transformation(
        self,
        agent_id: str,
        from_symbol: str,
        to_symbol: str,
        operation: Any,
        steps: List[str],
    ) -> TransformationTrace:
        """Record a multi-step symbolic transformation and return it.

        ``from_symbol`` is the label of the source symbol.
        ``to_symbol`` is the label of the target symbol. ``operation``
        accepts a ``SymbolicOperation`` member or its value/name string
        and classifies the overall transformation. ``steps`` is the
        ordered list of human-readable step descriptions that compose the
        transformation; it is copied so external mutation does not affect
        the stored trace. Raises ``RuntimeError`` if the trace registry
        is full.
        """
        with self._lock:
            if len(self._traces) >= self.MAX_TRACES:
                raise RuntimeError("trace registry is full")
            trace = TransformationTrace(
                agent_id=agent_id,
                from_symbol=str(from_symbol),
                to_symbol=str(to_symbol),
                operation=_resolve_enum(SymbolicOperation, operation),
                steps=[str(s) for s in (steps or [])],
                timestamp=_now(),
            )
            self._traces[trace.trace_id] = trace
            self._stats["total_traces"] += 1
            return trace

    def list_traces(
        self,
        agent_id: Optional[str] = None,
        limit: int = DEFAULT_LIST_LIMIT,
    ) -> List[TransformationTrace]:
        """Return transformation traces, optionally filtered by agent, capped to ``limit``.

        ``agent_id`` filters to traces recorded for that agent. ``limit``
        caps the number of results, applied after filtering. The returned
        list is ordered most-recent-last (insertion order) and is a
        snapshot copy; mutating it does not affect the engine.
        """
        with self._lock:
            traces = list(self._traces.values())
        if agent_id is not None:
            traces = [t for t in traces if t.agent_id == agent_id]
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = self.DEFAULT_LIST_LIMIT
        if n < 0:
            n = 0
        return traces[-n:] if n else []

    def get_trace(self, trace_id: str) -> Optional[TransformationTrace]:
        """Retrieve a transformation trace by id, or ``None`` if absent."""
        with self._lock:
            return self._traces.get(trace_id)

    # ── Profiles ──────────────────────────────────────────────────

    def get_profile(self, agent_id: str) -> SymbologyProfile:
        """Return the agent's symbology profile, creating it if absent.

        When a profile does not yet exist for the agent, a fresh one is
        computed from the agent's currently recorded symbols, actions, and
        encodings: ``total_symbols`` is the count of registered symbols,
        ``avg_density`` is the mean density contribution across those
        symbols (zero when there are none), ``dominant_type`` is the
        modal symbol type (or ``None`` when there are no symbols),
        ``regime`` is derived from the action count via
        ``_determine_regime``, ``total_encodings`` is the count of
        encoding attempts, and ``total_operations`` is the count of
        actions. The profile is then stored so subsequent callers can
        fetch the same object.
        """
        with self._lock:
            existing = self._profiles.get(agent_id)
            if existing is not None:
                return existing
            agent_symbols = self._agent_symbols(agent_id)
            agent_actions = self._agent_actions(agent_id)
            agent_encodings = self._agent_encodings(agent_id)
            total_symbols = len(agent_symbols)
            if total_symbols > 0:
                avg_density = sum(
                    s.density_contribution for s in agent_symbols
                ) / total_symbols
            else:
                avg_density = 0.0
            profile = SymbologyProfile(
                agent_id=agent_id,
                total_symbols=total_symbols,
                avg_density=avg_density,
                dominant_type=self._dominant_type(agent_symbols),
                regime=_determine_regime(len(agent_actions)),
                total_encodings=len(agent_encodings),
                total_operations=len(agent_actions),
                last_updated=_now(),
            )
            self._profiles[agent_id] = profile
            return profile

    def update_profile(self, agent_id: str, **kwargs: Any) -> SymbologyProfile:
        """Update fields on an agent's symbology profile and return it.

        The profile is fetched (or created) first, then each keyword in
        ``kwargs`` is applied to the matching attribute. ``dominant_type``
        and ``regime`` may be supplied as enum members or their value/name
        strings; they are normalized to enum members. ``dominant_type``
        may also be supplied as ``None`` to clear it. ``avg_density`` is
        coerced to a float and clamped to [0, 1]. ``total_symbols``,
        ``total_encodings``, and ``total_operations`` are coerced to
        integers. Unknown keys are ignored so callers can pass through
        generic update payloads safely.
        """
        with self._lock:
            profile = self.get_profile(agent_id)
            for key, value in kwargs.items():
                if key == "dominant_type":
                    if value is None:
                        profile.dominant_type = None
                    else:
                        profile.dominant_type = _resolve_enum(
                            SymbolType, value
                        )
                elif key == "regime":
                    profile.regime = _resolve_enum(TransformationRegime, value)
                elif key == "avg_density":
                    profile.avg_density = _clamp(value, 0.0, 1.0)
                elif key in (
                    "total_symbols",
                    "total_encodings",
                    "total_operations",
                ):
                    try:
                        setattr(profile, key, int(value))
                    except (TypeError, ValueError):
                        pass
                elif hasattr(profile, key):
                    setattr(profile, key, value)
            profile.last_updated = _now()
            return profile

    def list_profiles(self) -> List[SymbologyProfile]:
        """Return all stored symbology profiles as a snapshot list.

        The returned list is a snapshot copy; mutating it does not affect
        the engine.
        """
        with self._lock:
            return list(self._profiles.values())

    # ── Statistics ────────────────────────────────────────────────

    def get_stats(self) -> SymbologyStats:
        """Compute aggregate statistics over the current engine state.

        Totals are read from the running counter dict maintained by the
        record methods. ``density_distribution`` is tallied from stored
        snapshots and keyed by the density ``.value`` string.
        ``type_distribution`` is tallied from stored symbols and keyed by
        the symbol type ``.value`` string. ``operation_distribution`` is
        tallied from stored actions and keyed by the operation ``.value``
        string. All three dicts are plain ``Dict[str, int]`` so the result
        is JSON-serializable directly.
        """
        with self._lock:
            s = self._stats
            density_dist: Dict[str, int] = {}
            for snap in self._snapshots.values():
                key = _enum_value(SymbolicDensity, snap.density)
                density_dist[key] = density_dist.get(key, 0) + 1
            type_dist: Dict[str, int] = {}
            for sym in self._symbols.values():
                key = _enum_value(SymbolType, sym.symbol_type)
                type_dist[key] = type_dist.get(key, 0) + 1
            operation_dist: Dict[str, int] = {}
            for act in self._actions.values():
                key = _enum_value(SymbolicOperation, act.operation)
                operation_dist[key] = operation_dist.get(key, 0) + 1
            return SymbologyStats(
                total_symbols=int(s["total_symbols"]),
                total_actions=int(s["total_actions"]),
                total_encodings=int(s["total_encodings"]),
                total_snapshots=int(s["total_snapshots"]),
                total_traces=int(s["total_traces"]),
                density_distribution=density_dist,
                type_distribution=type_dist,
                operation_distribution=operation_dist,
            )

    # ── Maintenance ───────────────────────────────────────────────

    def reset(self) -> None:
        """Clear all engine state. Intended for tests.

        Drops every symbol, action, encoding attempt, snapshot,
        transformation trace, and profile, and re-initializes the running
        counters. After reset the engine behaves as if freshly
        constructed. The lock itself is not replaced.
        """
        with self._lock:
            self._symbols.clear()
            self._actions.clear()
            self._encodings.clear()
            self._snapshots.clear()
            self._traces.clear()
            self._profiles.clear()
            self._stats.clear()
            self._stats.update(
                {
                    "total_symbols": 0,
                    "total_actions": 0,
                    "total_encodings": 0,
                    "total_snapshots": 0,
                    "total_traces": 0,
                }
            )


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional["AgentCognitiveSymbology"] = None
_engine_lock = threading.Lock()


def get_symbology_engine() -> AgentCognitiveSymbology:
    """Get or create the singleton ``AgentCognitiveSymbology`` instance.

    The first call constructs the engine; subsequent calls return the same
    instance. Access is guarded by a module-level lock so the singleton is
    safe to initialize from multiple threads.
    """
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = AgentCognitiveSymbology()
        return _engine


def reset_symbology_engine() -> None:
    """Reset the singleton ``AgentCognitiveSymbology`` instance.

    Clears any state held by the current engine (if one exists) and drops
    the reference so the next ``get_symbology_engine`` call creates a fresh
    instance. Useful for tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        if _engine is not None:
            _engine.reset()
        _engine = None
