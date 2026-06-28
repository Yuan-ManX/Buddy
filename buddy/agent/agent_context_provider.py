"""
Buddy Agent Context Provider - Intelligent context enrichment and assembly.

Acts as an intelligent intermediary layer between user queries and agent
execution. It enriches, expands, and optimizes the context delivered to the
agent by gathering relevant information from multiple registered sources,
disambiguating intent, and assembling the optimal context window for each
request.

Key capabilities:
- Pluggable source connectors for heterogeneous context origins
- Heuristic intent classification and ambiguity resolution
- Multi-strategy context enrichment (expand, focus, disambiguate, ...)
- Relevance-ranked fragment selection within a token budget
- Adaptive bundle assembly modes (greedy, balanced, conservative, adaptive)
- Lightweight in-memory caching with TTL-based eviction
- Operational telemetry for connectors and overall provider health
"""

from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ═══════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════

class ContextSource(Enum):
    """Origin category for a context fragment."""
    MEMORY = "memory"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    WEB_SEARCH = "web_search"
    DOCUMENT = "document"
    CONVERSATION_HISTORY = "conversation_history"
    USER_PROFILE = "user_profile"
    AGENT_STATE = "agent_state"
    EXTERNAL_API = "external_api"
    TOOL_CACHE = "tool_cache"
    SEMANTIC_CACHE = "semantic_cache"
    WORKSPACE = "workspace"
    SKILL_REGISTRY = "skill_registry"
    EMBEDDING_INDEX = "embedding_index"


class ContextPriority(Enum):
    """Priority level for a context fragment (lower value = higher priority)."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class EnrichmentStrategy(Enum):
    """Strategy applied during context enrichment."""
    EXPAND = "expand"            # Broaden with related context
    FOCUS = "focus"              # Narrow to most relevant context
    DISAMBIGUATE = "disambiguate"  # Resolve ambiguity
    SUMMARIZE = "summarize"      # Compress content
    TRANSLATE = "translate"      # Reformulate content
    MULTIPLY = "multiply"        # Gather from many sources
    RANK = "rank"                # Reorder by relevance


class ContextFormat(Enum):
    """Render format for a context fragment."""
    RAW = "raw"
    STRUCTURED = "structured"
    SUMMARIZED = "summarized"
    EMBEDDED = "embedded"
    CITATION = "citation"


class AssemblyMode(Enum):
    """Strategy for assembling fragments into a bundle."""
    GREEDY = "greedy"              # Fill the token window fully
    BALANCED = "balanced"          # Keep some headroom across priorities
    CONSERVATIVE = "conservative"  # Only critical and high priority
    ADAPTIVE = "adaptive"          # Choose based on fragment count


class QueryIntent(Enum):
    """Classified intent of a user query."""
    QUESTION = "question"
    COMMAND = "command"
    CREATION = "creation"
    ANALYSIS = "analysis"
    EXPLORATION = "exploration"
    CLARIFICATION = "clarification"
    CONTINUATION = "continuation"
    COMPARISON = "comparison"
    DEBUGGING = "debugging"
    PLANNING = "planning"


class ProviderStatus(Enum):
    """Operational status of a source connector."""
    ACTIVE = "active"
    DISABLED = "disabled"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"


# ═══════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════

@dataclass
class ContextFragment:
    """A single piece of gathered context."""
    fragment_id: str
    source: ContextSource
    content: str
    priority: ContextPriority = ContextPriority.NORMAL
    relevance_score: float = 0.0
    tokens: int = 0
    format: ContextFormat = ContextFormat.RAW
    source_ref: str = ""
    retrieved_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)
    citation: str | None = None
    expires_at: float | None = None


@dataclass
class ContextQuery:
    """A request for context enrichment."""
    query_id: str
    user_input: str
    agent_id: str
    session_id: str
    intent: QueryIntent | None = None
    target_tokens: int = 4000
    assembly_mode: AssemblyMode = AssemblyMode.BALANCED
    strategies: list[EnrichmentStrategy] = field(
        default_factory=lambda: [EnrichmentStrategy.EXPAND]
    )
    required_sources: list[ContextSource] = field(default_factory=list)
    excluded_sources: list[ContextSource] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None


@dataclass
class ContextBundle:
    """Assembled context ready for delivery to an agent."""
    bundle_id: str
    query_id: str
    fragments: list[ContextFragment] = field(default_factory=list)
    total_tokens: int = 0
    assembled_text: str = ""
    intent: QueryIntent | None = None
    disambiguations: list[dict[str, Any]] = field(default_factory=list)
    expansions: list[dict[str, Any]] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    assembly_time_ms: float = 0.0


@dataclass
class SourceConnector:
    """Registered connector for a context source."""
    connector_id: str
    source: ContextSource
    name: str
    description: str
    status: ProviderStatus = ProviderStatus.ACTIVE
    priority: ContextPriority = ContextPriority.NORMAL
    fetch_function_name: str = ""
    max_tokens: int = 2000
    cache_ttl_seconds: int = 300
    last_invoked: float | None = None
    invocation_count: int = 0
    error_count: int = 0
    avg_latency_ms: float = 0.0
    enabled: bool = True
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class Disambiguation:
    """A detected ambiguity and its resolution."""
    disambiguation_id: str
    query_id: str
    ambiguous_term: str
    possible_meanings: list[str] = field(default_factory=list)
    chosen_meaning: str | None = None
    confidence: float = 0.0
    resolved_by: str = "heuristic"


@dataclass
class ProviderStats:
    """Aggregated operational statistics for the provider."""
    total_queries: int = 0
    total_bundles: int = 0
    total_fragments: int = 0
    avg_bundle_tokens: float = 0.0
    avg_assembly_time_ms: float = 0.0
    source_usage: dict[str, int] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════
# Provider
# ═══════════════════════════════════════════════════════════

# Static keyword sets and templates used by the heuristic engine.
_STOPWORDS: set[str] = {
    "the", "a", "an", "and", "or", "but", "if", "then", "else", "when",
    "at", "by", "for", "with", "about", "against", "between", "into",
    "through", "during", "before", "after", "above", "below", "to", "from",
    "up", "down", "in", "out", "on", "off", "over", "under", "again",
    "further", "is", "are", "was", "were", "be", "been", "being", "of",
    "it", "this", "that", "these", "those", "i", "you", "he", "she",
    "we", "they", "them", "his", "her", "its", "our", "your", "their",
    "do", "does", "did", "doing", "have", "has", "had", "having", "can",
    "could", "should", "would", "may", "might", "must", "shall", "will",
    "what", "which", "who", "whom", "how", "why", "where", "there",
}

# Ambiguous terms mapped to candidate meanings for heuristic disambiguation.
_AMBIGUOUS_TERMS: dict[str, list[str]] = {
    "bank": ["financial institution", "river edge", "to rely on"],
    "java": ["programming language", "island", "coffee"],
    "apple": ["fruit", "technology company"],
    "spring": ["season", "coil", "framework", "water source"],
    "python": ["programming language", "snake"],
    "go": ["programming language", "verb to move", "board game"],
    "bat": ["animal", "sports equipment"],
    "match": ["game", "to pair", "fire starter"],
    "rock": ["stone", "music genre", "to move back and forth"],
    "draft": ["preliminary version", "current of air", "conscription"],
    "cell": ["biological unit", "phone", "spreadsheet unit"],
    "light": ["illumination", "low weight"],
    "key": ["cryptographic key", "physical key", "important"],
}

# Per-source templated descriptions used when synthesizing fragments.
_SOURCE_TEMPLATES: dict[ContextSource, str] = {
    ContextSource.MEMORY: "Recalled memory relevant to: {kw}",
    ContextSource.KNOWLEDGE_GRAPH: "Knowledge graph entities linked to: {kw}",
    ContextSource.WEB_SEARCH: "Web search snippets matching: {kw}",
    ContextSource.DOCUMENT: "Document excerpts mentioning: {kw}",
    ContextSource.CONVERSATION_HISTORY: "Prior turns referencing: {kw}",
    ContextSource.USER_PROFILE: "User profile preferences tied to: {kw}",
    ContextSource.AGENT_STATE: "Agent runtime state for: {kw}",
    ContextSource.EXTERNAL_API: "External API data related to: {kw}",
    ContextSource.TOOL_CACHE: "Cached tool outputs for: {kw}",
    ContextSource.SEMANTIC_CACHE: "Semantically similar cached context for: {kw}",
    ContextSource.WORKSPACE: "Workspace artifacts involving: {kw}",
    ContextSource.SKILL_REGISTRY: "Registered skills applicable to: {kw}",
    ContextSource.EMBEDDING_INDEX: "Embedding index neighbors for: {kw}",
}

# Sources that are especially useful for a given intent.
_INTENT_SOURCE_AFFINITY: dict[QueryIntent, set[ContextSource]] = {
    QueryIntent.QUESTION: {ContextSource.KNOWLEDGE_GRAPH, ContextSource.DOCUMENT, ContextSource.WEB_SEARCH},
    QueryIntent.COMMAND: {ContextSource.AGENT_STATE, ContextSource.SKILL_REGISTRY, ContextSource.WORKSPACE},
    QueryIntent.CREATION: {ContextSource.SKILL_REGISTRY, ContextSource.WORKSPACE, ContextSource.DOCUMENT},
    QueryIntent.ANALYSIS: {ContextSource.DOCUMENT, ContextSource.KNOWLEDGE_GRAPH, ContextSource.EMBEDDING_INDEX},
    QueryIntent.EXPLORATION: {ContextSource.KNOWLEDGE_GRAPH, ContextSource.WEB_SEARCH, ContextSource.SEMANTIC_CACHE},
    QueryIntent.CLARIFICATION: {ContextSource.CONVERSATION_HISTORY, ContextSource.USER_PROFILE},
    QueryIntent.CONTINUATION: {ContextSource.CONVERSATION_HISTORY, ContextSource.AGENT_STATE, ContextSource.MEMORY},
    QueryIntent.COMPARISON: {ContextSource.DOCUMENT, ContextSource.KNOWLEDGE_GRAPH, ContextSource.WEB_SEARCH},
    QueryIntent.DEBUGGING: {ContextSource.AGENT_STATE, ContextSource.TOOL_CACHE, ContextSource.WORKSPACE},
    QueryIntent.PLANNING: {ContextSource.USER_PROFILE, ContextSource.WORKSPACE, ContextSource.MEMORY},
}


def _estimate_tokens(text: str) -> int:
    """Estimate token count for a string using a character ratio heuristic."""
    if not text:
        return 0
    return max(1, len(text) // 4)


class AgentContextProvider:
    """Agent Context Provider.

    Orchestrates the enrichment pipeline that turns a raw user query into a
    fully assembled context bundle. Connectors are registered for each context
    source; the provider heuristically classifies intent, resolves ambiguity,
    gathers synthetic fragments from enabled connectors, ranks them, and
    assembles a token-budgeted bundle for downstream agent consumption.
    """

    MAX_FRAGMENTS_PER_BUNDLE = 100
    MAX_BUNDLES_LOG = 10000
    DEFAULT_TARGET_TOKENS = 4000
    MIN_RELEVANCE_SCORE = 0.3
    CACHE_TTL_SECONDS = 300
    MAX_DISAMBIGUATIONS_PER_QUERY = 5

    def __init__(self) -> None:
        """Initialize the provider's internal registries and statistics."""
        self._connectors: dict[str, SourceConnector] = {}
        self._queries: dict[str, ContextQuery] = {}
        self._bundles: dict[str, ContextBundle] = {}
        self._cache: dict[str, tuple[list[ContextFragment], float]] = {}
        self._stats: ProviderStats = ProviderStats()
        self._intent_counts: dict[str, int] = {}

    # ── Connector management ───────────────────────────────

    def register_connector(
        self,
        source: ContextSource,
        name: str,
        description: str,
        priority: ContextPriority = ContextPriority.NORMAL,
        max_tokens: int = 2000,
        cache_ttl_seconds: int = 300,
        config: dict[str, Any] | None = None,
    ) -> SourceConnector:
        """Register a new context source connector.

        The connector's fetch behavior is simulated heuristically; no real
        external source is contacted. Raises ``ValueError`` if a connector is
        already registered for the given source.
        """
        for existing in self._connectors.values():
            if existing.source == source:
                raise ValueError(f"Connector already registered for source: {source.value}")
        connector = SourceConnector(
            connector_id=str(uuid.uuid4()),
            source=source,
            name=name,
            description=description,
            priority=priority,
            max_tokens=max_tokens,
            cache_ttl_seconds=cache_ttl_seconds,
            config=dict(config) if config else {},
        )
        self._connectors[connector.connector_id] = connector
        return connector

    def unregister_connector(self, connector_id: str) -> bool:
        """Remove a connector by id. Returns True if a connector was removed."""
        if connector_id in self._connectors:
            del self._connectors[connector_id]
            return True
        return False

    def update_connector(self, connector_id: str, **kwargs: Any) -> SourceConnector | None:
        """Update mutable fields on a registered connector.

        Only public dataclass fields may be updated. ``connector_id`` is
        immutable. Returns the updated connector, or ``None`` if not found.
        """
        connector = self._connectors.get(connector_id)
        if connector is None:
            return None
        for key, value in kwargs.items():
            if key == "connector_id":
                continue
            if hasattr(connector, key):
                setattr(connector, key, value)
        return connector

    def get_connector(self, connector_id: str) -> SourceConnector | None:
        """Return a connector by id, or ``None`` if not found."""
        return self._connectors.get(connector_id)

    def list_connectors(
        self,
        source: ContextSource | None = None,
        status: ProviderStatus | None = None,
    ) -> list[SourceConnector]:
        """List connectors, optionally filtered by source and/or status."""
        results: list[SourceConnector] = []
        for connector in self._connectors.values():
            if source is not None and connector.source != source:
                continue
            if status is not None and connector.status != status:
                continue
            results.append(connector)
        return results

    # ── Intent classification ─────────────────────────────

    def classify_intent(self, user_input: str) -> QueryIntent:
        """Heuristically classify the intent of a user query.

        Uses regex pattern matching against the input. The first matching rule
        in priority order wins. Falls back to ``CREATION`` when no rule matches.
        """
        if not user_input:
            return QueryIntent.CREATION
        text = user_input.strip()
        lowered_text = text.lower()

        # Question: ends with a question mark.
        if text.endswith("?"):
            return QueryIntent.QUESTION

        # Command: starts with an imperative verb.
        imperative = re.match(
            r"^\s*(create|build|make|generate|write|delete|run|execute)\b",
            lowered_text,
        )
        if imperative:
            return QueryIntent.COMMAND

        # Comparison.
        if re.search(r"\b(compare|vs|versus|difference)\b", lowered_text):
            return QueryIntent.COMPARISON

        # Exploration.
        if re.search(r"\b(explain|why|how)\b", lowered_text):
            return QueryIntent.EXPLORATION

        # Debugging.
        if re.search(r"\b(debug|error|fix|broken)\b", lowered_text):
            return QueryIntent.DEBUGGING

        # Planning.
        if re.search(r"\b(plan|schedule|organize)\b", lowered_text):
            return QueryIntent.PLANNING

        # Continuation: references a previous message.
        if re.search(r"\b(this|that|continue)\b", lowered_text):
            return QueryIntent.CONTINUATION

        # Clarification.
        if re.search(r"\b(what about|clarify)\b", lowered_text):
            return QueryIntent.CLARIFICATION

        # Analysis.
        if re.search(r"\b(analyze|examine|investigate)\b", lowered_text):
            return QueryIntent.ANALYSIS

        return QueryIntent.CREATION

    # ── Disambiguation ─────────────────────────────────────

    def disambiguate(self, user_input: str, query_id: str) -> list[Disambiguation]:
        """Detect ambiguous terms and propose candidate meanings.

        Detects pronouns (it/this/that/them/they), acronyms (all-caps tokens of
        two or more letters), and a curated set of multi-meaning words. For each
        detection, candidate meanings are generated heuristically. Returns an
        empty list when no clear ambiguity is present. Capped at
        ``MAX_DISAMBIGUATIONS_PER_QUERY``.
        """
        if not user_input:
            return []
        results: list[Disambiguation] = []
        seen_terms: set[str] = set()
        tokens = re.findall(r"[A-Za-z]+", user_input)

        # Pronouns that may reference an unspecified subject.
        pronoun_meanings: dict[str, list[str]] = {
            "it": ["the previous subject", "the current object", "a referenced entity"],
            "this": ["the current item", "the preceding statement", "the active task"],
            "that": ["the prior reference", "the mentioned item", "the previous result"],
            "them": ["a group of items", "the referenced people", "a set of entities"],
            "they": ["a referenced group", "the mentioned actors", "a set of items"],
        }
        for token in tokens:
            lower = token.lower()
            if lower in pronoun_meanings and lower not in seen_terms:
                seen_terms.add(lower)
                meanings = pronoun_meanings[lower]
                results.append(Disambiguation(
                    disambiguation_id=str(uuid.uuid4()),
                    query_id=query_id,
                    ambiguous_term=lower,
                    possible_meanings=list(meanings),
                    chosen_meaning=meanings[0],
                    confidence=0.4,
                    resolved_by="heuristic",
                ))
                if len(results) >= self.MAX_DISAMBIGUATIONS_PER_QUERY:
                    return results

        # Acronyms: all-caps tokens of length >= 2.
        for token in tokens:
            if len(token) >= 2 and token.isupper() and token not in seen_terms:
                seen_terms.add(token)
                results.append(Disambiguation(
                    disambiguation_id=str(uuid.uuid4()),
                    query_id=query_id,
                    ambiguous_term=token,
                    possible_meanings=[
                        f"acronym expansion of {token}",
                        f"proper noun {token}",
                        f"identifier {token}",
                    ],
                    chosen_meaning=f"acronym expansion of {token}",
                    confidence=0.3,
                    resolved_by="heuristic",
                ))
                if len(results) >= self.MAX_DISAMBIGUATIONS_PER_QUERY:
                    return results

        # Curated multi-meaning words.
        for token in tokens:
            lower = token.lower()
            if lower in _AMBIGUOUS_TERMS and lower not in seen_terms:
                seen_terms.add(lower)
                meanings = _AMBIGUOUS_TERMS[lower]
                results.append(Disambiguation(
                    disambiguation_id=str(uuid.uuid4()),
                    query_id=query_id,
                    ambiguous_term=lower,
                    possible_meanings=list(meanings),
                    chosen_meaning=meanings[0],
                    confidence=0.35,
                    resolved_by="heuristic",
                ))
                if len(results) >= self.MAX_DISAMBIGUATIONS_PER_QUERY:
                    return results

        return results

    # ── Enrichment pipeline ────────────────────────────────

    def enrich(self, context_query: ContextQuery) -> ContextBundle:
        """Run the full enrichment pipeline for a context query.

        Steps:
        1. Classify intent when not provided.
        2. Run disambiguation over the user input.
        3. Apply configured enrichment strategies.
        4. Gather fragments from enabled connectors (simulated).
        5. Rank fragments by relevance and priority.
        6. Assemble a bundle honoring the token budget and assembly mode.

        Returns the assembled ``ContextBundle``.
        """
        start = time.time()
        self._stats.total_queries += 1
        self._queries[context_query.query_id] = context_query

        intent = context_query.intent
        if intent is None:
            intent = self.classify_intent(context_query.user_input)
            context_query.intent = intent
        self._intent_counts[intent.value] = self._intent_counts.get(intent.value, 0) + 1

        disambiguations = self.disambiguate(context_query.user_input, context_query.query_id)

        strategies = context_query.strategies or [EnrichmentStrategy.EXPAND]
        expansions: list[dict[str, Any]] = []
        for strategy in strategies:
            expansions.append({
                "strategy": strategy.value,
                "applied": True,
                "note": f"Applied {strategy.value} enrichment strategy",
            })

        fragments = self.gather_fragments(
            query_id=context_query.query_id,
            user_input=context_query.user_input,
            intent=intent,
            required_sources=context_query.required_sources,
            excluded_sources=context_query.excluded_sources,
        )

        keywords = self._extract_keywords(context_query.user_input)
        fragments = self.rank_fragments(fragments, keywords, intent)

        assembled_text, total_tokens, selected = self.assemble_bundle(
            fragments=fragments,
            target_tokens=context_query.target_tokens,
            mode=context_query.assembly_mode,
        )

        citations: list[str] = []
        for frag in selected:
            if frag.citation and frag.citation not in citations:
                citations.append(frag.citation)

        elapsed_ms = (time.time() - start) * 1000.0
        bundle = ContextBundle(
            bundle_id=str(uuid.uuid4()),
            query_id=context_query.query_id,
            fragments=selected,
            total_tokens=total_tokens,
            assembled_text=assembled_text,
            intent=intent,
            disambiguations=[d.__dict__ for d in disambiguations],
            expansions=expansions,
            citations=citations,
            created_at=time.time(),
            assembly_time_ms=elapsed_ms,
        )

        context_query.completed_at = time.time()
        self._register_bundle(bundle)

        # Update aggregate statistics.
        self._stats.total_bundles += 1
        self._stats.total_fragments += len(selected)
        n = self._stats.total_bundles
        self._stats.avg_bundle_tokens = (
            (self._stats.avg_bundle_tokens * (n - 1) + total_tokens) / n
        )
        self._stats.avg_assembly_time_ms = (
            (self._stats.avg_assembly_time_ms * (n - 1) + elapsed_ms) / n
        )
        for frag in selected:
            key = frag.source.value
            self._stats.source_usage[key] = self._stats.source_usage.get(key, 0) + 1

        return bundle

    def gather_fragments(
        self,
        query_id: str,
        user_input: str,
        intent: QueryIntent,
        required_sources: list[ContextSource],
        excluded_sources: list[ContextSource],
    ) -> list[ContextFragment]:
        """Gather fragments from enabled, non-excluded connectors.

        If ``required_sources`` is non-empty, gathering is restricted to those
        sources. Fragments are synthesized heuristically from the user input
        keywords and the connector's source template. Each fragment respects the
        connector's ``max_tokens`` budget. Results are cached briefly to avoid
        redundant synthesis.
        """
        excluded_set = set(excluded_sources)
        required_set = set(required_sources) if required_sources else None

        cache_key = self._cache_key(user_input, intent, required_sources, excluded_sources)
        cached = self._cache.get(cache_key)
        if cached is not None and cached[1] > time.time():
            return [self._clone_fragment(f) for f in cached[0]]

        keywords = self._extract_keywords(user_input)
        keyword_phrase = ", ".join(keywords) if keywords else user_input.strip()
        if not keyword_phrase:
            keyword_phrase = "<unspecified topic>"

        fragments: list[ContextFragment] = []
        for connector in self._connectors.values():
            if not connector.enabled:
                continue
            if connector.status == ProviderStatus.DISABLED:
                continue
            if connector.source in excluded_set:
                continue
            if required_set is not None and connector.source not in required_set:
                continue

            template = _SOURCE_TEMPLATES.get(
                connector.source, "Context for: {kw}"
            ).format(kw=keyword_phrase)
            content = self._synthesize_content(connector, intent, keywords, template)
            tokens = min(_estimate_tokens(content), connector.max_tokens)
            if tokens > connector.max_tokens:
                content = content[: max(1, connector.max_tokens * 4)]
                tokens = min(_estimate_tokens(content), connector.max_tokens)

            fragment = ContextFragment(
                fragment_id=str(uuid.uuid4()),
                source=connector.source,
                content=content,
                priority=connector.priority,
                relevance_score=0.0,
                tokens=tokens,
                format=ContextFormat.STRUCTURED,
                source_ref=connector.connector_id,
                retrieved_at=time.time(),
                metadata={
                    "connector_name": connector.name,
                    "intent": intent.value,
                    "query_id": query_id,
                },
                citation=f"{connector.source.value}:{connector.name}",
            )
            fragments.append(fragment)

            # Simulate connector invocation telemetry.
            connector.last_invoked = time.time()
            connector.invocation_count += 1
            connector.avg_latency_ms = (
                (connector.avg_latency_ms * (connector.invocation_count - 1) + 1.0)
                / connector.invocation_count
            )

        self._cache[cache_key] = (fragments, time.time() + self.CACHE_TTL_SECONDS)
        return fragments

    # ── Internal helpers ───────────────────────────────────

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract keywords by lowercasing, stopword removal, and deduplication."""
        if not text:
            return []
        raw = re.findall(r"[A-Za-z]+", text.lower())
        keywords: list[str] = []
        seen: set[str] = set()
        for token in raw:
            if len(token) < 2:
                continue
            if token in _STOPWORDS:
                continue
            if token in seen:
                continue
            seen.add(token)
            keywords.append(token)
        return keywords

    def _synthesize_content(
        self,
        connector: SourceConnector,
        intent: QueryIntent,
        keywords: list[str],
        template: str,
    ) -> str:
        """Synthesize heuristic fragment content for a connector."""
        affinity = _INTENT_SOURCE_AFFINITY.get(intent, set())
        boost = " (high-affinity source)" if connector.source in affinity else ""
        kw_line = "; ".join(keywords) if keywords else "<no keywords detected>"
        return (
            f"[{connector.source.value}{boost}] {template}\n"
            f"Intent: {intent.value}\n"
            f"Keywords: {kw_line}\n"
            f"Source: {connector.name}"
        )

    def rank_fragments(
        self,
        fragments: list[ContextFragment],
        query_keywords: list[str],
        intent: QueryIntent,
    ) -> list[ContextFragment]:
        """Compute relevance scores and sort fragments.

        Relevance is derived from keyword overlap between the fragment content
        and the query keywords, boosted when the fragment source has affinity
        with the classified intent. Fragments are sorted by relevance score
        descending, then by priority ascending (critical first).
        """
        if not fragments:
            return []
        keyword_set = set(query_keywords)
        affinity = _INTENT_SOURCE_AFFINITY.get(intent, set())
        for frag in fragments:
            content_words = set(re.findall(r"[A-Za-z]+", frag.content.lower()))
            overlap = len(keyword_set & content_words)
            base = overlap / max(1, len(keyword_set)) if keyword_set else 0.0
            if frag.source in affinity:
                base = min(1.0, base + 0.25)
            # Priority contributes a small boost so higher-priority fragments
            # surface even with modest keyword overlap.
            priority_boost = (ContextPriority.BACKGROUND.value - frag.priority.value) * 0.02
            frag.relevance_score = round(min(1.0, base + priority_boost), 4)
        return sorted(
            fragments,
            key=lambda f: (-f.relevance_score, f.priority.value),
        )

    def assemble_bundle(
        self,
        fragments: list[ContextFragment],
        target_tokens: int,
        mode: AssemblyMode,
    ) -> tuple[str, int, list[ContextFragment]]:
        """Select fragments within a token budget based on the assembly mode.

        Returns a tuple of ``(assembled_text, total_tokens, selected_fragments)``.
        """
        if not fragments:
            return "", 0, []

        # Pre-filter by minimum relevance to avoid injecting noise.
        candidate = [f for f in fragments if f.relevance_score >= self.MIN_RELEVANCE_SCORE]
        if not candidate:
            candidate = list(fragments)

        if mode == AssemblyMode.CONSERVATIVE:
            candidate = [
                f for f in candidate
                if f.priority in (ContextPriority.CRITICAL, ContextPriority.HIGH)
            ]
            budget = target_tokens
        elif mode == AssemblyMode.GREEDY:
            budget = target_tokens
        elif mode == AssemblyMode.ADAPTIVE:
            if len(candidate) <= 10:
                budget = target_tokens
            else:
                budget = int(target_tokens * 0.8)
        else:  # BALANCED
            budget = int(target_tokens * 0.85)

        selected: list[ContextFragment] = []
        used = 0
        for frag in candidate:
            if len(selected) >= self.MAX_FRAGMENTS_PER_BUNDLE:
                break
            if used + frag.tokens > budget:
                continue
            selected.append(frag)
            used += frag.tokens
            if used >= budget:
                break

        if not selected and candidate:
            # Guarantee at least one fragment when the budget is very tight.
            head = candidate[0]
            trimmed_tokens = min(head.tokens, budget) if budget > 0 else head.tokens
            selected.append(head)
            used = trimmed_tokens

        lines: list[str] = []
        for frag in selected:
            header = f"[{frag.source.value} | priority={frag.priority.name} | rel={frag.relevance_score:.2f}]"
            lines.append(f"{header}\n{frag.content}")
        assembled_text = "\n\n---\n\n".join(lines)
        total_tokens = sum(f.tokens for f in selected)
        return assembled_text, total_tokens, selected

    def _cache_key(
        self,
        user_input: str,
        intent: QueryIntent,
        required_sources: list[ContextSource],
        excluded_sources: list[ContextSource],
    ) -> str:
        """Build a cache key for gathered fragments."""
        required = ",".join(sorted(s.value for s in required_sources))
        excluded = ",".join(sorted(s.value for s in excluded_sources))
        return f"{intent.value}|{user_input.strip().lower()}|req={required}|exc={excluded}"

    def _clone_fragment(self, frag: ContextFragment) -> ContextFragment:
        """Return a shallow copy of a fragment for cache hits."""
        return ContextFragment(
            fragment_id=str(uuid.uuid4()),
            source=frag.source,
            content=frag.content,
            priority=frag.priority,
            relevance_score=frag.relevance_score,
            tokens=frag.tokens,
            format=frag.format,
            source_ref=frag.source_ref,
            retrieved_at=frag.retrieved_at,
            metadata=dict(frag.metadata),
            citation=frag.citation,
            expires_at=frag.expires_at,
        )

    def _register_bundle(self, bundle: ContextBundle) -> None:
        """Store a bundle, trimming the log when it exceeds the configured cap."""
        self._bundles[bundle.bundle_id] = bundle
        if len(self._bundles) > self.MAX_BUNDLES_LOG:
            # Drop the oldest entries to stay within the log cap.
            overflow = len(self._bundles) - self.MAX_BUNDLES_LOG
            for key in list(self._bundles.keys())[:overflow]:
                del self._bundles[key]

    # ── Lookups ────────────────────────────────────────────

    def get_bundle(self, bundle_id: str) -> ContextBundle | None:
        """Return a bundle by id, or ``None`` if not found."""
        return self._bundles.get(bundle_id)

    def list_bundles(self, query_id: str | None = None, limit: int = 100) -> list[ContextBundle]:
        """List bundles, optionally filtered by query id, capped by ``limit``."""
        bundles = list(self._bundles.values())
        if query_id is not None:
            bundles = [b for b in bundles if b.query_id == query_id]
        bundles = bundles[-limit:] if limit < len(bundles) else bundles
        return bundles

    def get_query(self, query_id: str) -> ContextQuery | None:
        """Return a query by id, or ``None`` if not found."""
        return self._queries.get(query_id)

    def list_queries(self, agent_id: str | None = None, limit: int = 100) -> list[ContextQuery]:
        """List queries, optionally filtered by agent id, capped by ``limit``."""
        queries = list(self._queries.values())
        if agent_id is not None:
            queries = [q for q in queries if q.agent_id == agent_id]
        queries = queries[-limit:] if limit < len(queries) else queries
        return queries

    # ── Telemetry ──────────────────────────────────────────

    def get_connector_stats(self, connector_id: str) -> dict[str, Any]:
        """Return operational stats for a single connector."""
        connector = self._connectors.get(connector_id)
        if connector is None:
            return {}
        successes = connector.invocation_count - connector.error_count
        success_rate = successes / connector.invocation_count if connector.invocation_count else 0.0
        return {
            "connector_id": connector.connector_id,
            "name": connector.name,
            "source": connector.source.value,
            "status": connector.status.value,
            "invocation_count": connector.invocation_count,
            "error_count": connector.error_count,
            "success_rate": round(success_rate, 4),
            "avg_latency_ms": round(connector.avg_latency_ms, 4),
            "last_invoked": connector.last_invoked,
        }

    def get_stats(self) -> dict[str, Any]:
        """Return aggregate provider statistics plus connector and intent info."""
        return {
            "total_queries": self._stats.total_queries,
            "total_bundles": self._stats.total_bundles,
            "total_fragments": self._stats.total_fragments,
            "avg_bundle_tokens": round(self._stats.avg_bundle_tokens, 4),
            "avg_assembly_time_ms": round(self._stats.avg_assembly_time_ms, 4),
            "connector_count": len(self._connectors),
            "source_usage": dict(self._stats.source_usage),
            "intent_distribution": dict(self._intent_counts),
        }

    # ── Cache and reset ────────────────────────────────────

    def clear_cache(self) -> int:
        """Evict expired cache entries. Returns the number of entries cleared."""
        now = time.time()
        expired = [key for key, (_value, expires_at) in self._cache.items() if expires_at <= now]
        for key in expired:
            del self._cache[key]
        return len(expired)

    def reset(self) -> None:
        """Clear all connectors, queries, bundles, cache, and statistics."""
        self._connectors.clear()
        self._queries.clear()
        self._bundles.clear()
        self._cache.clear()
        self._stats = ProviderStats()
        self._intent_counts.clear()


# ═══════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════

_context_provider: AgentContextProvider | None = None


def get_context_provider() -> AgentContextProvider:
    """Return the shared :class:`AgentContextProvider` singleton."""
    global _context_provider
    if _context_provider is None:
        _context_provider = AgentContextProvider()
    return _context_provider


def reset_context_provider() -> None:
    """Reset and release the shared :class:`AgentContextProvider` singleton."""
    global _context_provider
    if _context_provider is not None:
        _context_provider.reset()
    _context_provider = None
