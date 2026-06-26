"""
Buddy Intent Resolution Engine - Comprehensive intent understanding and disambiguation.

Provides a multi-signal classification system that resolves user intents through
lexical, semantic, contextual, and historical signal analysis. Handles ambiguous
intents with confidence scoring, breaks complex intents into ordered sub-intents,
and tracks user intent patterns over time for adaptive personalization.

Key capabilities:
- Multi-signal intent classification (lexical, semantic, contextual, historical)
- Ambiguous intent disambiguation with confidence-weighted options
- Complex intent decomposition into dependency-ordered sub-intents
- Named entity extraction with positional metadata
- User intent profile building and pattern tracking
- Automatic tool suggestion based on intent category
- Multi-turn intent refinement with resolution tracing
"""

from __future__ import annotations

import re
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ═══════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════

class IntentCategory(str, Enum):
    """Primary categories of user intent."""
    INFORMATION_SEEKING = "information_seeking"
    TASK_EXECUTION = "task_execution"
    CREATIVE_GENERATION = "creative_generation"
    ANALYSIS = "analysis"
    CONVERSATION = "conversation"
    COMMAND = "command"
    QUESTION = "question"
    CLARIFICATION = "clarification"
    EXPLORATION = "exploration"
    META = "meta"


class ComplexityLevel(str, Enum):
    """Complexity classification for intents."""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"
    EXPERT = "expert"


class UrgencyLevel(str, Enum):
    """Urgency classification for intents."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SubIntentStatus(str, Enum):
    """Status of a sub-intent during resolution."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    DEFERRED = "deferred"
    FAILED = "failed"


class SignalType(str, Enum):
    """Types of signals used in intent classification."""
    LEXICAL = "lexical"
    SEMANTIC = "semantic"
    CONTEXTUAL = "contextual"
    HISTORICAL = "historical"


# ═══════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════

@dataclass
class Entity:
    """A named entity extracted from the user prompt."""
    type: str
    value: str
    confidence: float
    position: tuple[int, int]  # (start_char, end_char) in the prompt
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SubIntent:
    """A decomposed sub-intent from a complex parent intent."""
    id: str
    category: IntentCategory
    description: str
    priority: int
    depends_on: list[str] = field(default_factory=list)
    status: SubIntentStatus = SubIntentStatus.PENDING
    confidence: float = 0.0
    required_tools: list[str] = field(default_factory=list)
    estimated_complexity: ComplexityLevel = ComplexityLevel.SIMPLE
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DisambiguationOption:
    """A possible resolution for an ambiguous intent."""
    category: IntentCategory
    description: str
    confidence: float
    supporting_signals: list[SignalType] = field(default_factory=list)
    entity_matches: list[Entity] = field(default_factory=list)


@dataclass
class DisambiguatedIntent:
    """Result of resolving an ambiguous intent."""
    intent_id: str
    original_options: list[DisambiguationOption]
    selected_option: DisambiguationOption
    resolved_at: float = field(default_factory=time.time)
    resolution_method: str = "user_selection"


@dataclass
class IntentResult:
    """Complete result of intent resolution."""
    id: str
    primary_intent: IntentCategory
    confidence: float
    sub_intents: list[SubIntent] = field(default_factory=list)
    entities: list[Entity] = field(default_factory=list)
    complexity: ComplexityLevel = ComplexityLevel.SIMPLE
    urgency: UrgencyLevel = UrgencyLevel.LOW
    required_capabilities: list[str] = field(default_factory=list)
    suggested_tools: list[str] = field(default_factory=list)
    expected_output_format: str = "text"
    ambiguity_score: float = 0.0
    disambiguation_options: list[DisambiguationOption] = field(default_factory=list)
    resolution_trace: list[dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    context_used: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class IntentPattern:
    """A recognized pattern in a user's intent history."""
    pattern_id: str
    category: IntentCategory
    frequency: int = 0
    last_seen: float = field(default_factory=time.time)
    avg_confidence: float = 0.0
    common_entities: list[str] = field(default_factory=list)
    preferred_tools: list[str] = field(default_factory=list)
    correlated_categories: list[IntentCategory] = field(default_factory=list)


@dataclass
class IntentProfile:
    """A user's accumulated intent patterns and preferences."""
    user_id: str
    frequent_intents: dict[IntentCategory, int] = field(default_factory=dict)
    patterns: list[IntentPattern] = field(default_factory=list)
    preferred_formats: dict[str, int] = field(default_factory=dict)
    last_updated: float = field(default_factory=time.time)
    total_interactions: int = 0
    average_ambiguity: float = 0.0
    common_entities: dict[str, int] = field(default_factory=dict)
    complexity_distribution: dict[ComplexityLevel, int] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════
# Intent Resolution Engine
# ═══════════════════════════════════════════════════════════

class IntentResolutionEngine:
    """Comprehensive intent resolution engine for the Buddy AI agent platform.

    Resolves user intents through multi-signal classification, handles ambiguity
    through confidence scoring and disambiguation, decomposes complex intents
    into dependency-ordered sub-intents, and builds user intent profiles over time.

    The engine uses four signal dimensions:
    - Lexical: keyword and pattern matching on the prompt text
    - Semantic: structural analysis of phrasing, complexity, and format
    - Contextual: conversation history and surrounding context signals
    - Historical: user-specific intent patterns and preferences
    """

    # ── Lexical signal tables ──────────────────────────────────────

    _LEXICAL_SIGNALS: dict[IntentCategory, list[str]] = {
        IntentCategory.INFORMATION_SEEKING: [
            "what is", "how does", "tell me about", "explain", "describe",
            "define", "information on", "details about", "look up", "find out",
            "research", "overview of", "summary of", "background on",
        ],
        IntentCategory.TASK_EXECUTION: [
            "do", "execute", "run", "perform", "complete", "accomplish",
            "carry out", "process", "handle", "take care of", "get this done",
            "make it happen", "implement", "deploy", "build",
        ],
        IntentCategory.CREATIVE_GENERATION: [
            "write", "create", "generate", "compose", "design", "draft",
            "produce", "craft", "develop", "invent", "brainstorm", "imagine",
            "story", "poem", "article", "script", "draw", "paint",
        ],
        IntentCategory.ANALYSIS: [
            "analyze", "compare", "evaluate", "assess", "review", "examine",
            "investigate", "inspect", "audit", "diagnose", "break down",
            "understand why", "what caused", "root cause", "trend",
        ],
        IntentCategory.CONVERSATION: [
            "hi", "hello", "hey", "how are you", "good morning", "good evening",
            "what's up", "chat", "talk", "discuss", "let's talk about",
            "opinion on", "what do you think", "casual", "friendly",
        ],
        IntentCategory.COMMAND: [
            "set", "update", "delete", "remove", "add", "change", "modify",
            "configure", "enable", "disable", "start", "stop", "restart",
            "open", "close", "save", "load", "reset", "clear",
        ],
        IntentCategory.QUESTION: [
            "what", "why", "when", "where", "who", "which", "how", "can you",
            "could you", "would you", "is it", "are there", "should i",
            "do you", "does it",
        ],
        IntentCategory.CLARIFICATION: [
            "what do you mean", "can you clarify", "elaborate", "explain that",
            "i don't understand", "could you repeat", "rephrase", "simpler",
            "in other words", "what does that mean", "clarify",
        ],
        IntentCategory.EXPLORATION: [
            "explore", "discover", "browse", "navigate", "what can you",
            "what are the possibilities", "show me options", "what's available",
            "list", "enumerate", "possibilities", "alternatives",
        ],
        IntentCategory.META: [
            "what can you do", "your capabilities", "how do you work",
            "what are you", "who are you", "your limits", "your features",
            "self", "about yourself", "your purpose", "system", "settings",
            "preferences", "configure yourself",
        ],
    }

    _URGENCY_SIGNALS: dict[str, UrgencyLevel] = {
        "urgent": UrgencyLevel.CRITICAL,
        "asap": UrgencyLevel.CRITICAL,
        "immediately": UrgencyLevel.CRITICAL,
        "critical": UrgencyLevel.CRITICAL,
        "emergency": UrgencyLevel.CRITICAL,
        "right now": UrgencyLevel.CRITICAL,
        "hurry": UrgencyLevel.CRITICAL,
        "important": UrgencyLevel.HIGH,
        "priority": UrgencyLevel.HIGH,
        "soon": UrgencyLevel.HIGH,
        "quickly": UrgencyLevel.HIGH,
        "deadline": UrgencyLevel.HIGH,
        "whenever": UrgencyLevel.LOW,
        "no rush": UrgencyLevel.LOW,
        "sometime": UrgencyLevel.LOW,
        "eventually": UrgencyLevel.LOW,
    }

    _COMPLEXITY_MARKERS: dict[str, ComplexityLevel] = {
        "multi-step": ComplexityLevel.EXPERT,
        "pipeline": ComplexityLevel.EXPERT,
        "workflow": ComplexityLevel.EXPERT,
        "architecture": ComplexityLevel.EXPERT,
        "system design": ComplexityLevel.EXPERT,
        "orchestrate": ComplexityLevel.COMPLEX,
        "integrate": ComplexityLevel.COMPLEX,
        "end-to-end": ComplexityLevel.COMPLEX,
        "full stack": ComplexityLevel.COMPLEX,
        "ecosystem": ComplexityLevel.COMPLEX,
    }

    _TOOL_SUGGESTIONS: dict[IntentCategory, list[str]] = {
        IntentCategory.INFORMATION_SEEKING: ["web_search", "knowledge_base", "rag_retriever", "document_reader"],
        IntentCategory.TASK_EXECUTION: ["task_runner", "code_executor", "file_editor", "terminal", "scheduler"],
        IntentCategory.CREATIVE_GENERATION: ["content_generator", "template_engine", "markdown_renderer", "image_generator"],
        IntentCategory.ANALYSIS: ["data_analyzer", "chart_generator", "log_analyzer", "statistics_engine"],
        IntentCategory.CONVERSATION: ["memory_retriever", "persona_selector", "conversation_manager"],
        IntentCategory.COMMAND: ["file_editor", "system_tools", "config_manager", "deployment_tool"],
        IntentCategory.QUESTION: ["web_search", "knowledge_base", "qa_engine", "reasoning_engine"],
        IntentCategory.CLARIFICATION: ["context_explainer", "example_generator", "simplifier"],
        IntentCategory.EXPLORATION: ["browser", "search_engine", "discovery_agent", "suggestion_engine"],
        IntentCategory.META: ["capability_registry", "config_manager", "self_diagnostics"],
    }

    _CAPABILITY_MAP: dict[IntentCategory, list[str]] = {
        IntentCategory.INFORMATION_SEEKING: ["knowledge_retrieval", "web_access", "summarization"],
        IntentCategory.TASK_EXECUTION: ["code_execution", "tool_use", "multi_step_planning"],
        IntentCategory.CREATIVE_GENERATION: ["text_generation", "structured_output", "creativity"],
        IntentCategory.ANALYSIS: ["reasoning", "computation", "data_processing", "pattern_recognition"],
        IntentCategory.CONVERSATION: ["dialogue_management", "persona_adaptation", "memory_recall"],
        IntentCategory.COMMAND: ["system_access", "state_modification", "tool_orchestration"],
        IntentCategory.QUESTION: ["factual_recall", "reasoning", "knowledge_retrieval"],
        IntentCategory.CLARIFICATION: ["context_tracking", "paraphrasing", "explanation"],
        IntentCategory.EXPLORATION: ["search", "discovery", "recommendation", "browsing"],
        IntentCategory.META: ["self_awareness", "configuration", "diagnostics"],
    }

    _OUTPUT_FORMATS: dict[IntentCategory, str] = {
        IntentCategory.INFORMATION_SEEKING: "markdown",
        IntentCategory.TASK_EXECUTION: "action_result",
        IntentCategory.CREATIVE_GENERATION: "text",
        IntentCategory.ANALYSIS: "structured_report",
        IntentCategory.CONVERSATION: "text",
        IntentCategory.COMMAND: "confirmation",
        IntentCategory.QUESTION: "markdown",
        IntentCategory.CLARIFICATION: "text",
        IntentCategory.EXPLORATION: "list",
        IntentCategory.META: "text",
    }

    # ── Entity extraction patterns ─────────────────────────────────

    _ENTITY_PATTERNS: list[tuple[str, str, str]] = [
        # (type, regex pattern, description)
        ("email", r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', "Email address"),
        ("url", r'\bhttps?://[^\s<>"]+|www\.[^\s<>"]+', "URL"),
        ("file_path", r'(?:~|/|[A-Za-z]:\\)(?:[^\s:*?"<>|]+/)*[^\s:*?"<>|]*\.[a-zA-Z0-9]+', "File path"),
        ("version", r'\b\d+\.\d+(?:\.\d+)?(?:-[a-zA-Z0-9]+)?\b', "Version number"),
        ("date", r'\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}/\d{1,2}/\d{2,4}\b', "Date"),
        ("programming_language", r'\b(Python|JavaScript|TypeScript|Go|Rust|Java|C\+\+|C#|Ruby|PHP|Swift|Kotlin|Scala|R|Dart|Lua|Perl|Haskell|Elixir|Clojure)\b', "Programming language"),
        ("framework", r'\b(React|Vue|Angular|Django|Flask|FastAPI|Express|Spring|Rails|Laravel|Next\.js|Nuxt|Svelte|TensorFlow|PyTorch|Keras|Pandas|NumPy)\b', "Framework"),
        ("database", r'\b(PostgreSQL|MySQL|MongoDB|Redis|SQLite|Elasticsearch|Cassandra|DynamoDB|Neo4j|MariaDB|Oracle|ClickHouse|Snowflake)\b', "Database"),
        ("cloud_service", r'\b(AWS|S3|EC2|Lambda|Azure|GCP|Kubernetes|Docker|Terraform|CloudFront|Cloudflare|Vercel|Netlify|Heroku)\b', "Cloud service"),
        ("number", r'\b\d+(?:\.\d+)?(?:[kmb]b?)?\b', "Numeric value"),
        ("command", r'\b(git|npm|pip|docker|kubectl|curl|wget|ssh|scp|rsync|make|cargo|go|brew|apt|yum|chmod|ls|cd|mkdir|cp|mv|rm)\b', "CLI command"),
        ("os", r'\b(Linux|macOS|Windows|Ubuntu|Debian|Fedora|CentOS|Arch|Alpine)\b', "Operating system"),
    ]

    # ── Sub-intent decomposition patterns ──────────────────────────

    _SUB_INTENT_SEPARATORS: list[str] = [
        " and ", " then ", " after that ", " also ", " additionally ",
        " furthermore ", " moreover ", " next ", " finally ", " first ",
        " second ", " third ", " lastly ", " subsequently ",
    ]

    _STEP_INDICATORS: list[str] = [
        "step 1", "step 2", "step 3", "first,", "second,", "third,",
        "1.", "2.", "3.", "1)", "2)", "3)", "- ", "* ",
    ]

    def __init__(self):
        self._profiles: dict[str, IntentProfile] = {}
        self._resolution_cache: dict[str, IntentResult] = {}
        self._history: dict[str, list[IntentResult]] = {}  # user_id -> recent intents
        self._total_resolutions: int = 0
        self._ambiguity_threshold: float = 0.35

    # ── Public API ─────────────────────────────────────────────────

    def resolve(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
        history: list[dict[str, Any]] | None = None,
    ) -> IntentResult:
        """Resolve a user prompt into a structured intent result.

        Performs multi-signal classification, entity extraction, ambiguity
        detection, and sub-intent decomposition. Incorporates contextual and
        historical signals when available.

        Args:
            prompt: The raw user prompt text.
            context: Optional contextual metadata (e.g., session info, active tools).
            history: Optional conversation history for multi-turn refinement.

        Returns:
            An IntentResult with the fully resolved intent.
        """
        ctx = context or {}
        hist = history or []

        intent_id = f"int-{uuid.uuid4().hex[:12]}"
        trace: list[dict[str, Any]] = []

        # Step 1: Lexical classification
        lexical_scores = self._score_lexical(prompt)
        trace.append({"step": "lexical_classification", "scores": lexical_scores})

        # Step 2: Semantic classification
        semantic_scores = self._score_semantic(prompt)
        trace.append({"step": "semantic_classification", "scores": semantic_scores})

        # Step 3: Contextual signal adjustment
        contextual_adjustments = self._score_contextual(prompt, ctx, hist)
        trace.append({"step": "contextual_adjustment", "adjustments": contextual_adjustments})

        # Step 4: Historical signal adjustment
        if "user_id" in ctx:
            historical_adjustments = self._score_historical(ctx["user_id"], prompt)
            trace.append({"step": "historical_adjustment", "adjustments": historical_adjustments})
        else:
            historical_adjustments = {}

        # Step 5: Fuse signals into final classification
        fused_scores = self._fuse_signals(
            lexical_scores, semantic_scores,
            contextual_adjustments, historical_adjustments,
        )
        trace.append({"step": "signal_fusion", "fused_scores": fused_scores})

        primary_category, confidence = self._select_primary(fused_scores)
        trace.append({"step": "primary_selection", "category": primary_category.value, "confidence": confidence})

        # Step 6: Extract entities
        entities = self.extract_entities(prompt)
        trace.append({"step": "entity_extraction", "entity_count": len(entities)})

        # Step 7: Detect ambiguity
        ambiguity_score, disambiguation_options = self._detect_ambiguity(fused_scores)
        trace.append({"step": "ambiguity_detection", "ambiguity_score": ambiguity_score})

        # Step 8: Assess complexity and urgency
        complexity = self._assess_complexity(prompt, entities, primary_category)
        urgency = self._assess_urgency(prompt, ctx, hist)
        trace.append({"step": "complexity_urgency", "complexity": complexity.value, "urgency": urgency.value})

        # Step 9: Decompose sub-intents if complex
        sub_intents: list[SubIntent] = []
        if complexity in (ComplexityLevel.COMPLEX, ComplexityLevel.EXPERT) or ambiguity_score > 0.3:
            sub_intents = self.detect_sub_intents(intent_id)
            trace.append({"step": "sub_intent_decomposition", "sub_intent_count": len(sub_intents)})

        # Step 10: Suggest tools and capabilities
        suggested_tools = self._suggest_tools(primary_category, prompt, entities)
        required_capabilities = self._CAPABILITY_MAP.get(primary_category, [])
        output_format = self._OUTPUT_FORMATS.get(primary_category, "text")

        # Build result
        result = IntentResult(
            id=intent_id,
            primary_intent=primary_category,
            confidence=confidence,
            sub_intents=sub_intents,
            entities=entities,
            complexity=complexity,
            urgency=urgency,
            required_capabilities=required_capabilities,
            suggested_tools=suggested_tools,
            expected_output_format=output_format,
            ambiguity_score=ambiguity_score,
            disambiguation_options=disambiguation_options,
            resolution_trace=trace,
            context_used={
                "has_context": bool(ctx),
                "has_history": bool(hist),
                "context_keys": list(ctx.keys()) if ctx else [],
                "history_turns": len(hist) if hist else 0,
            },
            metadata={
                "prompt_length": len(prompt),
                "word_count": len(prompt.split()),
                "signal_count": len(trace),
            },
        )

        # Cache and track
        self._resolution_cache[intent_id] = result
        self._total_resolutions += 1

        # Update user profile if available
        if "user_id" in ctx:
            user_id = ctx["user_id"]
            self._update_profile(user_id, result)
            if user_id not in self._history:
                self._history[user_id] = []
            self._history[user_id].append(result)
            if len(self._history[user_id]) > 100:
                self._history[user_id] = self._history[user_id][-100:]

        return result

    def disambiguate(
        self,
        intent_id: str,
        options: list[dict[str, Any]],
    ) -> DisambiguatedIntent:
        """Resolve an ambiguous intent by selecting from disambiguation options.

        Args:
            intent_id: The ID of the ambiguous intent result.
            options: A list of option dicts, each with at least 'category' and 'description'.
                     The first option is treated as the user's selection.

        Returns:
            A DisambiguatedIntent with the resolved selection.
        """
        cached = self._resolution_cache.get(intent_id)

        disambiguation_options: list[DisambiguationOption] = []
        for opt in options:
            cat = IntentCategory(opt["category"]) if isinstance(opt["category"], str) else opt["category"]
            disambiguation_options.append(DisambiguationOption(
                category=cat,
                description=opt.get("description", ""),
                confidence=opt.get("confidence", 0.5),
                supporting_signals=opt.get("supporting_signals", []),
                entity_matches=opt.get("entity_matches", []),
            ))

        selected = disambiguation_options[0] if disambiguation_options else DisambiguationOption(
            category=IntentCategory.QUESTION,
            description="Fallback option",
            confidence=0.3,
        )

        resolved = DisambiguatedIntent(
            intent_id=intent_id,
            original_options=disambiguation_options,
            selected_option=selected,
            resolution_method="user_selection",
        )

        # Update cached result if available
        if cached:
            cached.primary_intent = selected.category
            cached.confidence = max(cached.confidence, selected.confidence)
            cached.ambiguity_score = 0.0
            cached.disambiguation_options = []
            cached.resolution_trace.append({
                "step": "disambiguation",
                "selected": selected.category.value,
                "confidence": selected.confidence,
            })

        return resolved

    def classify(self, prompt: str) -> IntentCategory:
        """Classify a prompt into a single intent category.

        Performs a lightweight lexical and semantic classification without
        the full resolution pipeline. Suitable for quick routing decisions.

        Args:
            prompt: The user prompt to classify.

        Returns:
            The classified IntentCategory.
        """
        lexical = self._score_lexical(prompt)
        semantic = self._score_semantic(prompt)
        fused = self._fuse_signals(lexical, semantic, {}, {})
        category, _ = self._select_primary(fused)
        return category

    def extract_entities(self, prompt: str) -> list[Entity]:
        """Extract named entities from the prompt text.

        Uses regex-based pattern matching to identify entities such as
        emails, URLs, file paths, programming languages, frameworks,
        databases, cloud services, and more.

        Args:
            prompt: The text to extract entities from.

        Returns:
            A list of Entity objects with type, value, confidence, and position.
        """
        entities: list[Entity] = []
        seen_spans: set[tuple[int, int]] = set()

        for entity_type, pattern, _description in self._ENTITY_PATTERNS:
            for match in re.finditer(pattern, prompt, re.IGNORECASE):
                start, end = match.span()
                # Avoid overlapping matches
                if any(
                    start < s_end and end > s_start
                    for s_start, s_end in seen_spans
                ):
                    continue
                seen_spans.add((start, end))
                entities.append(Entity(
                    type=entity_type,
                    value=match.group(0),
                    confidence=self._compute_entity_confidence(entity_type, match.group(0)),
                    position=(start, end),
                    metadata={"raw_text": match.group(0)},
                ))

        return entities

    def detect_sub_intents(self, intent_id: str) -> list[SubIntent]:
        """Break down a complex intent into ordered sub-intents.

        Analyzes the original prompt associated with the intent_id to
        identify separable sub-intents with dependency ordering. Returns
        an empty list for simple intents.

        Args:
            intent_id: The ID of the intent to decompose.

        Returns:
            A list of SubIntent objects with dependency ordering.
        """
        cached = self._resolution_cache.get(intent_id)
        if not cached:
            return []

        # Use the original prompt from metadata or entities
        prompt = cached.metadata.get("prompt", "")
        if not prompt:
            # Reconstruct from entities
            return []

        sub_intents: list[SubIntent] = []
        segments = self._segment_prompt(prompt)

        if len(segments) <= 1:
            return []

        for idx, segment in enumerate(segments):
            seg_category = self.classify(segment)
            sub_id = f"{intent_id}-sub-{idx}"
            sub = SubIntent(
                id=sub_id,
                category=seg_category,
                description=segment.strip()[:200],
                priority=idx,
                depends_on=[f"{intent_id}-sub-{idx - 1}"] if idx > 0 else [],
                status=SubIntentStatus.PENDING,
                confidence=0.7,
                required_tools=self._suggest_tools(seg_category, segment, []),
                estimated_complexity=self._assess_complexity(segment, [], seg_category),
                metadata={"segment_index": idx, "original_segment": segment},
            )
            sub_intents.append(sub)

        return sub_intents

    def get_intent_profile(self, user_id: str) -> IntentProfile:
        """Build or retrieve a user's intent profile.

        Creates a new profile if one doesn't exist, otherwise returns the
        accumulated profile with intent patterns, frequency distributions,
        and format preferences.

        Args:
            user_id: The unique identifier for the user.

        Returns:
            An IntentProfile with the user's accumulated intent data.
        """
        if user_id not in self._profiles:
            self._profiles[user_id] = IntentProfile(user_id=user_id)
        return self._profiles[user_id]

    def reset(self) -> None:
        """Clear all internal state, profiles, cache, and history."""
        self._profiles.clear()
        self._resolution_cache.clear()
        self._history.clear()
        self._total_resolutions = 0

    def get_stats(self) -> dict[str, Any]:
        """Get engine statistics."""
        return {
            "total_resolutions": self._total_resolutions,
            "cached_resolutions": len(self._resolution_cache),
            "tracked_users": len(self._profiles),
            "users_with_history": len(self._history),
            "ambiguity_threshold": self._ambiguity_threshold,
        }

    # ── Internal: Lexical scoring ──────────────────────────────────

    def _score_lexical(self, prompt: str) -> dict[IntentCategory, float]:
        """Score intent categories based on lexical keyword matching."""
        scores: dict[IntentCategory, float] = {}
        prompt_lower = prompt.lower()

        for category, signals in self._LEXICAL_SIGNALS.items():
            score = 0.0
            matches = 0
            for signal in signals:
                if signal in prompt_lower:
                    matches += 1
                    # Bonus for signals at the start of the prompt
                    idx = prompt_lower.find(signal)
                    if idx == 0 or (idx > 0 and prompt_lower[idx - 1] in " \t\n"):
                        score += 1.0
                    else:
                        score += 0.6
            if matches > 0:
                # Normalize: more matches = higher confidence, with diminishing returns
                # Base score from the strongest match contribution, scaled by match count
                normalized = score / max(matches, 1)
                score = min(normalized, 1.0) * (1.0 - 0.3 ** matches)
            scores[category] = score

        return scores

    def _score_semantic(self, prompt: str) -> dict[IntentCategory, float]:
        """Score intent categories based on semantic/structural features."""
        scores: dict[IntentCategory, float] = {}
        prompt_lower = prompt.lower()
        word_count = len(prompt.split())

        # Question mark detection
        has_question_mark = "?" in prompt

        # Sentence structure
        sentences = [s.strip() for s in re.split(r'[.!?]+', prompt) if s.strip()]
        sentence_count = len(sentences)

        # Imperative detection (starts with verb)
        imperative_patterns = [
            r'^(?:please\s+)?(?:do|run|execute|set|create|get|find|show|tell|make|build|start|stop|open|close|delete|remove|add|update|change|check|list|print|display|generate|compile|install|configure|enable|disable|read|write|save|load|send|fetch|download|upload|deploy|test|debug|fix|optimize|refactor|format|validate|verify|merge|commit|push|pull|clone|sync|schedule|cancel|pause|resume|restart|clear|reset|export|import|convert|transform|analyze|compare|evaluate|calculate|compute|estimate|measure|track|monitor|log|audit|review|approve|reject|assign|notify|alert|warn)\b',
        ]
        is_imperative = any(
            re.search(pat, prompt_lower) for pat in imperative_patterns
        )

        # Greeting patterns
        greeting_patterns = [r'^(hi|hello|hey|good\s+(morning|afternoon|evening)|what\'?s?\s+up|howdy)\b']
        is_greeting = any(re.search(pat, prompt_lower) for pat in greeting_patterns)

        # Meta/self-referential patterns
        meta_patterns = [
            r'\b(you|your|yourself|your own)\b.*\b(capabilit|feature|limit|purpose|who are|what are)\b',
            r'\bwhat can you\b',
            r'\bwhat (do|are) you\b',
            r'\bhow (do|are|can) you\b',
            r'\bwho are you\b',
            r'\b(help|assist|support)\b.*\b(you can|your)\b',
        ]
        is_meta = any(re.search(pat, prompt_lower) for pat in meta_patterns)

        # Clarification patterns
        clarification_patterns = [
            r'\b(what do you mean|i don\'?t understand|can you (clarify|explain|elaborate|rephrase)|pardon|come again|simpler|in other words)\b',
        ]
        is_clarification = any(re.search(pat, prompt_lower) for pat in clarification_patterns)

        # Exploration patterns
        exploration_patterns = [
            r'\b(what (can|else|other|are the|options|possibilit)|show me|list|enumerate|browse|explore|discover)\b',
        ]
        is_exploration = any(re.search(pat, prompt_lower) for pat in exploration_patterns)

        # Analysis indicators
        analysis_indicators = [
            r'\b(compare|versus|vs\.?|difference between|pros and cons|trade[\s-]off|benchmark|performance of|better than|worse than)\b',
        ]
        has_analysis_indicators = any(re.search(pat, prompt_lower) for pat in analysis_indicators)

        # Creative indicators
        creative_indicators = [
            r'\b(write (a|an|the|some)|compose|draft|create (a|an|the)|generate (a|an|the)|story|poem|article|blog|essay|script|novel|song|lyrics)\b',
        ]
        has_creative_indicators = any(re.search(pat, prompt_lower) for pat in creative_indicators)

        # Information-seeking patterns
        info_seeking_patterns = [
            r'\b(explain|describe|tell me|define|elaborate on|what is|how does|how do|how to)\b',
        ]
        is_info_seeking = any(re.search(pat, prompt_lower) for pat in info_seeking_patterns)

        # Command-like structure (short, direct, imperative)
        is_command_like = word_count <= 5 and is_imperative and not has_question_mark

        # Question structure
        is_question = has_question_mark or prompt_lower.startswith(("what", "why", "when", "where", "who", "which", "how", "can", "could", "would", "should", "is", "are", "do", "does", "did"))

        for category in IntentCategory:
            score = 0.0

            if category == IntentCategory.META and is_meta:
                score = 0.8
            elif category == IntentCategory.QUESTION and is_question:
                score = 0.7
                if word_count <= 10:
                    score = 0.85
                # Reduce if it looks like a meta question
                if is_meta:
                    score = 0.3
            elif category == IntentCategory.COMMAND and is_command_like:
                score = 0.8
            elif category == IntentCategory.COMMAND and is_imperative and word_count <= 8:
                score = 0.6
            elif category == IntentCategory.CONVERSATION and is_greeting:
                score = 0.85
            elif category == IntentCategory.META and is_meta:
                score = 0.8
            elif category == IntentCategory.CLARIFICATION and is_clarification:
                score = 0.75
            elif category == IntentCategory.EXPLORATION and is_exploration:
                score = 0.7
            elif category == IntentCategory.ANALYSIS and has_analysis_indicators:
                score = 0.65
            elif category == IntentCategory.CREATIVE_GENERATION and has_creative_indicators:
                score = 0.7
            elif category == IntentCategory.INFORMATION_SEEKING and is_question and word_count > 10:
                score = 0.5
            elif category == IntentCategory.INFORMATION_SEEKING and is_info_seeking:
                score = 0.65
            elif category == IntentCategory.TASK_EXECUTION and is_imperative and word_count > 5:
                score = 0.5

            # Complexity bonus for longer prompts
            if word_count > 30 and category in (IntentCategory.ANALYSIS, IntentCategory.TASK_EXECUTION):
                score += 0.1

            scores[category] = min(score, 1.0)

        return scores

    def _score_contextual(
        self,
        prompt: str,
        context: dict[str, Any],
        history: list[dict[str, Any]],
    ) -> dict[IntentCategory, float]:
        """Adjust scores based on contextual signals."""
        adjustments: dict[IntentCategory, float] = {}

        # If there's conversation history, boost conversation-related categories
        if history:
            # Check if this is a follow-up in a multi-turn exchange
            last_turn = history[-1] if history else {}
            last_content = last_turn.get("content", "") if isinstance(last_turn, dict) else ""

            if last_content:
                # Boost clarification if the last response was long/complex
                if len(last_content) > 500:
                    adjustments[IntentCategory.CLARIFICATION] = 0.2
                    adjustments[IntentCategory.QUESTION] = 0.15

                # Boost conversation continuity
                adjustments[IntentCategory.CONVERSATION] = 0.1

        # Context-based adjustments
        if context.get("active_tool"):
            adjustments[IntentCategory.COMMAND] = 0.25
            adjustments[IntentCategory.TASK_EXECUTION] = 0.2

        if context.get("in_code_session"):
            adjustments[IntentCategory.TASK_EXECUTION] = 0.3
            adjustments[IntentCategory.COMMAND] = 0.2

        if context.get("expecting_clarification"):
            adjustments[IntentCategory.CLARIFICATION] = 0.4

        return adjustments

    def _score_historical(
        self,
        user_id: str,
        prompt: str,
    ) -> dict[IntentCategory, float]:
        """Adjust scores based on user's historical intent patterns."""
        adjustments: dict[IntentCategory, float] = {}
        profile = self._profiles.get(user_id)

        if not profile or not profile.frequent_intents:
            return adjustments

        total_intents = profile.total_interactions
        if total_intents < 3:
            return adjustments

        # Boost categories that are frequently used by this user
        for category, count in profile.frequent_intents.items():
            frequency = count / total_intents
            if frequency > 0.3:
                adjustments[category] = 0.15
            elif frequency > 0.15:
                adjustments[category] = 0.08

        # Boost if the prompt text matches a known pattern
        prompt_lower = prompt.lower()
        for pattern in profile.patterns:
            if pattern.frequency > 5 and any(
                entity.lower() in prompt_lower
                for entity in pattern.common_entities
            ):
                adjustments[pattern.category] = adjustments.get(pattern.category, 0.0) + 0.1

        return adjustments

    # ── Internal: Signal fusion ────────────────────────────────────

    def _fuse_signals(
        self,
        lexical: dict[IntentCategory, float],
        semantic: dict[IntentCategory, float],
        contextual: dict[IntentCategory, float],
        historical: dict[IntentCategory, float],
    ) -> dict[IntentCategory, float]:
        """Fuse multiple signal dimensions into a unified score map.

        Weights: lexical=0.35, semantic=0.35, contextual=0.15, historical=0.15
        """
        weights = {
            SignalType.LEXICAL: 0.35,
            SignalType.SEMANTIC: 0.35,
            SignalType.CONTEXTUAL: 0.15,
            SignalType.HISTORICAL: 0.15,
        }

        fused: dict[IntentCategory, float] = {}

        for category in IntentCategory:
            lex = lexical.get(category, 0.0)
            sem = semantic.get(category, 0.0)
            ctx = contextual.get(category, 0.0)
            hist = historical.get(category, 0.0)

            fused[category] = (
                lex * weights[SignalType.LEXICAL]
                + sem * weights[SignalType.SEMANTIC]
                + ctx * weights[SignalType.CONTEXTUAL]
                + hist * weights[SignalType.HISTORICAL]
            )

        return fused

    def _select_primary(
        self,
        scores: dict[IntentCategory, float],
    ) -> tuple[IntentCategory, float]:
        """Select the primary intent category from fused scores."""
        if not scores:
            return IntentCategory.QUESTION, 0.3

        sorted_categories = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_category, top_score = sorted_categories[0]

        # If no category has a meaningful score, default to QUESTION
        if top_score < 0.05:
            return IntentCategory.QUESTION, 0.15

        return top_category, min(top_score, 1.0)

    # ── Internal: Ambiguity detection ──────────────────────────────

    def _detect_ambiguity(
        self,
        scores: dict[IntentCategory, float],
    ) -> tuple[float, list[DisambiguationOption]]:
        """Detect ambiguity by analyzing score distribution.

        Returns an ambiguity score (0.0-1.0) and a list of disambiguation
        options when the top categories are close in confidence.
        """
        sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        if len(sorted_items) < 2:
            return 0.0, []

        top_score = sorted_items[0][1]
        second_score = sorted_items[1][1]

        if top_score < 0.1:
            return 0.9, []

        # Ambiguity is high when the second-best is close to the best
        score_gap = top_score - second_score
        if score_gap <= 0.0:
            ambiguity = 0.9
        elif score_gap < 0.1:
            ambiguity = 0.7 - (score_gap * 5)
        elif score_gap < 0.2:
            ambiguity = 0.4 - (score_gap * 2)
        elif score_gap < 0.3:
            ambiguity = 0.2 - (score_gap * 1)
        else:
            ambiguity = 0.0

        options: list[DisambiguationOption] = []
        if ambiguity > self._ambiguity_threshold:
            # Include top N categories that are close
            for cat, score in sorted_items[:3]:
                if score > 0.05:
                    options.append(DisambiguationOption(
                        category=cat,
                        description=f"Intent appears to be {cat.value.replace('_', ' ')}",
                        confidence=score,
                        supporting_signals=[SignalType.LEXICAL, SignalType.SEMANTIC],
                    ))

        return min(ambiguity, 1.0), options

    # ── Internal: Complexity and urgency assessment ────────────────

    def _assess_complexity(
        self,
        prompt: str,
        entities: list[Entity],
        category: IntentCategory,
    ) -> ComplexityLevel:
        """Assess the complexity of the intent."""
        prompt_lower = prompt.lower()
        word_count = len(prompt.split())

        # Check for explicit complexity markers
        for marker, level in self._COMPLEXITY_MARKERS.items():
            if marker in prompt_lower:
                return level

        # Multi-clause detection
        separation_count = sum(
            1 for sep in self._SUB_INTENT_SEPARATORS if sep in prompt_lower
        )
        step_count = sum(
            1 for ind in self._STEP_INDICATORS if ind in prompt_lower
        )

        has_multi_part = separation_count > 0 or step_count > 0

        # Entity-based complexity
        entity_types = len(set(e.type for e in entities))

        # Category-specific complexity
        if category in (IntentCategory.TASK_EXECUTION, IntentCategory.ANALYSIS):
            if word_count > 80 or (has_multi_part and word_count > 40):
                return ComplexityLevel.EXPERT
            elif word_count > 40 or has_multi_part:
                return ComplexityLevel.COMPLEX
            elif word_count > 15:
                return ComplexityLevel.MEDIUM
            return ComplexityLevel.SIMPLE

        if category == IntentCategory.CREATIVE_GENERATION:
            if word_count > 50 or (has_multi_part and word_count > 25):
                return ComplexityLevel.COMPLEX
            elif word_count > 20 or has_multi_part:
                return ComplexityLevel.MEDIUM
            return ComplexityLevel.SIMPLE

        if category == IntentCategory.COMMAND:
            if has_multi_part and entity_types > 2:
                return ComplexityLevel.COMPLEX
            elif word_count > 10:
                return ComplexityLevel.MEDIUM
            return ComplexityLevel.SIMPLE

        # General complexity assessment
        if word_count > 60 or (has_multi_part and word_count > 30):
            return ComplexityLevel.COMPLEX
        elif word_count > 25 or has_multi_part:
            return ComplexityLevel.MEDIUM
        elif word_count > 10:
            return ComplexityLevel.MEDIUM
        return ComplexityLevel.SIMPLE

    def _assess_urgency(
        self,
        prompt: str,
        context: dict[str, Any],
        history: list[dict[str, Any]],
    ) -> UrgencyLevel:
        """Assess the urgency level of the intent."""
        prompt_lower = prompt.lower()

        # Check for explicit urgency keywords
        for keyword, level in self._URGENCY_SIGNALS.items():
            if keyword in prompt_lower:
                return level

        # Context-based urgency
        if context.get("priority") == "high" or context.get("urgent"):
            return UrgencyLevel.HIGH

        if context.get("deadline"):
            return UrgencyLevel.HIGH

        if context.get("priority") == "critical":
            return UrgencyLevel.CRITICAL

        # History-based urgency (escalating if multi-turn)
        if history and len(history) > 5:
            return UrgencyLevel.MEDIUM

        return UrgencyLevel.LOW

    # ── Internal: Entity extraction helpers ────────────────────────

    def _compute_entity_confidence(
        self,
        entity_type: str,
        value: str,
    ) -> float:
        """Compute confidence for an extracted entity."""
        # High-confidence types
        high_confidence_types = {"email", "url", "version", "date"}
        if entity_type in high_confidence_types:
            return 0.95

        # Programming languages have high confidence due to exact matching
        if entity_type == "programming_language":
            return 0.92

        # Frameworks and databases
        if entity_type in ("framework", "database", "cloud_service", "os"):
            return 0.90

        # File paths
        if entity_type == "file_path":
            return 0.85 if len(value) > 5 else 0.70

        # Commands
        if entity_type == "command":
            return 0.88

        # Numbers
        if entity_type == "number":
            return 0.80

        return 0.75

    # ── Internal: Prompt segmentation for sub-intents ──────────────

    def _segment_prompt(self, prompt: str) -> list[str]:
        """Split a prompt into segments for sub-intent decomposition."""
        # Try splitting by explicit separators
        segments: list[str] = []
        remaining = prompt

        for sep in self._SUB_INTENT_SEPARATORS:
            if sep in remaining:
                parts = remaining.split(sep)
                if len(parts) > 1:
                    segments.append(parts[0].strip())
                    remaining = sep.join(parts[1:])
                    break
        else:
            # Try step indicators
            for ind in self._STEP_INDICATORS:
                if ind in remaining.lower():
                    idx = remaining.lower().find(ind)
                    if idx > 0:
                        segments.append(remaining[:idx].strip())
                    remaining = remaining[idx + len(ind):].strip()
                    break

        if segments:
            segments.append(remaining.strip())
        else:
            # Try sentence-based splitting for long prompts
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', prompt) if s.strip()]
            if len(sentences) > 1:
                segments = sentences
            else:
                segments = [prompt]

        return [s for s in segments if s]

    # ── Internal: Tool suggestion ──────────────────────────────────

    def _suggest_tools(
        self,
        category: IntentCategory,
        prompt: str,
        entities: list[Entity],
    ) -> list[str]:
        """Suggest relevant tools based on intent category and entities."""
        suggestions = list(self._TOOL_SUGGESTIONS.get(category, []))

        # Entity-based additional suggestions
        entity_types = {e.type for e in entities}
        if "programming_language" in entity_types:
            if "code_executor" not in suggestions:
                suggestions.append("code_executor")
        if "file_path" in entity_types:
            if "file_editor" not in suggestions:
                suggestions.append("file_editor")
        if "database" in entity_types:
            if "database_client" not in suggestions:
                suggestions.append("database_client")
        if "cloud_service" in entity_types:
            if "deployment_tool" not in suggestions:
                suggestions.append("deployment_tool")

        return suggestions

    # ── Internal: Profile management ───────────────────────────────

    def _update_profile(
        self,
        user_id: str,
        result: IntentResult,
    ) -> None:
        """Update a user's intent profile with a new resolution result."""
        profile = self.get_intent_profile(user_id)

        # Update frequency counter
        cat = result.primary_intent
        profile.frequent_intents[cat] = profile.frequent_intents.get(cat, 0) + 1

        # Update total interactions
        profile.total_interactions += 1

        # Update complexity distribution
        profile.complexity_distribution[result.complexity] = (
            profile.complexity_distribution.get(result.complexity, 0) + 1
        )

        # Update entity tracking
        for entity in result.entities:
            profile.common_entities[entity.value] = (
                profile.common_entities.get(entity.value, 0) + 1
            )

        # Update format preferences
        fmt = result.expected_output_format
        profile.preferred_formats[fmt] = profile.preferred_formats.get(fmt, 0) + 1

        # Update ambiguity average
        n = profile.total_interactions
        profile.average_ambiguity = (
            profile.average_ambiguity * (n - 1) + result.ambiguity_score
        ) / n

        # Update or create pattern
        self._update_patterns(profile, result)

        profile.last_updated = time.time()

    def _update_patterns(
        self,
        profile: IntentProfile,
        result: IntentResult,
    ) -> None:
        """Update intent patterns in a user's profile."""
        pattern_id = f"pat-{result.primary_intent.value}"

        existing = None
        for pat in profile.patterns:
            if pat.pattern_id == pattern_id:
                existing = pat
                break

        if existing:
            existing.frequency += 1
            existing.last_seen = time.time()
            existing.avg_confidence = (
                existing.avg_confidence * (existing.frequency - 1) + result.confidence
            ) / existing.frequency
            for entity in result.entities:
                if entity.value not in existing.common_entities:
                    existing.common_entities.append(entity.value)
            for tool in result.suggested_tools:
                if tool not in existing.preferred_tools:
                    existing.preferred_tools.append(tool)
        else:
            new_pattern = IntentPattern(
                pattern_id=pattern_id,
                category=result.primary_intent,
                frequency=1,
                avg_confidence=result.confidence,
                common_entities=[e.value for e in result.entities],
                preferred_tools=list(result.suggested_tools),
            )
            profile.patterns.append(new_pattern)


# ═══════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════

_intent_resolution: IntentResolutionEngine | None = None


def get_intent_resolution() -> IntentResolutionEngine:
    """Get or create the global Intent Resolution Engine instance."""
    global _intent_resolution
    if _intent_resolution is None:
        _intent_resolution = IntentResolutionEngine()
    return _intent_resolution


def reset_intent_resolution() -> None:
    """Reset the global Intent Resolution Engine instance."""
    global _intent_resolution
    if _intent_resolution:
        _intent_resolution.reset()
    _intent_resolution = None