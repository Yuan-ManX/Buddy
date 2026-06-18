"""Buddy Context Engine — Agentic context management and orchestration

Intelligent context management system that assembles, compresses, injects,
and tracks context for agent prompts. Manages token budgets, sliding context
windows, and provides analytics on context usage efficiency.

Components:
- ContextAssembler: Builds optimal context from multiple sources
- ContextCompressor: Compresses context to fit token limits
- ContextInjector: Injects relevant context into agent prompts
- ContextWindow: Manages the sliding context window
- ContextAnalytics: Tracks context usage metrics and efficiency
"""

from __future__ import annotations

import logging
import re
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger("buddy.context_engine")


# ══════════════════════════════════════════════════════════════
# Enums
# ══════════════════════════════════════════════════════════════


class ContextSource(str, Enum):
    """Sources from which context can be drawn."""
    SYSTEM_PROMPT = "system_prompt"
    CONVERSATION_HISTORY = "conversation_history"
    MEMORY = "memory"
    TOOLS = "tools"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    PERSONA = "persona"


class ContextPriority(str, Enum):
    """Priority levels for context allocation."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CompressionStrategy(str, Enum):
    """Strategies for compressing context."""
    SUMMARIZATION = "summarization"
    ENTITY_EXTRACTION = "entity_extraction"
    TRUNCATION = "truncation"
    HYBRID = "hybrid"


# ══════════════════════════════════════════════════════════════
# Data Classes
# ══════════════════════════════════════════════════════════════


@dataclass
class ContextElement:
    """A single element of context from a specific source."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: ContextSource = ContextSource.SYSTEM_PROMPT
    content: str = ""
    token_count: int = 0
    priority: ContextPriority = ContextPriority.MEDIUM
    importance_score: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source.value,
            "content_preview": self.content[:100],
            "token_count": self.token_count,
            "priority": self.priority.value,
            "importance_score": self.importance_score,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


@dataclass
class ContextBudget:
    """Token budget allocation across context sources."""
    total_tokens: int = 8192
    allocations: dict[ContextSource, int] = field(default_factory=dict)
    reserved_tokens: int = 0
    used_tokens: int = 0

    def __post_init__(self):
        if not self.allocations:
            self._apply_default_allocations()

    def _apply_default_allocations(self):
        """Apply default priority-based token allocations."""
        self.allocations = {
            ContextSource.SYSTEM_PROMPT: int(self.total_tokens * 0.20),
            ContextSource.CONVERSATION_HISTORY: int(self.total_tokens * 0.40),
            ContextSource.MEMORY: int(self.total_tokens * 0.15),
            ContextSource.TOOLS: int(self.total_tokens * 0.10),
            ContextSource.KNOWLEDGE_GRAPH: int(self.total_tokens * 0.10),
            ContextSource.PERSONA: int(self.total_tokens * 0.05),
        }

    def remaining(self, source: ContextSource) -> int:
        allocated = self.allocations.get(source, 0)
        used = self._used_for_source(source)
        return max(0, allocated - used)

    def _used_for_source(self, source: ContextSource) -> int:
        return 0  # Updated externally during assembly

    def is_exhausted(self, source: ContextSource) -> bool:
        return self.remaining(source) <= 0

    def remaining_total(self) -> int:
        return max(0, self.total_tokens - self.used_tokens - self.reserved_tokens)


@dataclass
class CompressionResult:
    """Result of a context compression operation."""
    original_tokens: int = 0
    compressed_tokens: int = 0
    compression_ratio: float = 1.0
    strategy_used: CompressionStrategy = CompressionStrategy.HYBRID
    summary: str = ""
    extracted_entities: list[dict[str, Any]] = field(default_factory=list)
    key_points: list[str] = field(default_factory=list)
    importance_distribution: dict[str, float] = field(default_factory=dict)
    quality_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_tokens": self.original_tokens,
            "compressed_tokens": self.compressed_tokens,
            "compression_ratio": round(self.compression_ratio, 2),
            "strategy_used": self.strategy_used.value,
            "summary_preview": self.summary[:200],
            "entity_count": len(self.extracted_entities),
            "key_points_count": len(self.key_points),
            "quality_score": self.quality_score,
        }


@dataclass
class InjectResult:
    """Result of context injection into a prompt."""
    elements_injected: int = 0
    tokens_injected: int = 0
    sources_used: list[ContextSource] = field(default_factory=list)
    template_variables: dict[str, str] = field(default_factory=dict)
    relevance_scores: dict[str, float] = field(default_factory=dict)
    injection_latency_ms: float = 0.0


@dataclass
class WindowSnapshot:
    """Snapshot of the sliding context window state."""
    window_id: str = ""
    total_elements: int = 0
    total_tokens: int = 0
    oldest_element_age: float = 0.0
    newest_element_age: float = 0.0
    source_distribution: dict[str, int] = field(default_factory=dict)
    is_overfull: bool = False
    overflow_count: int = 0
    snapshot_time: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class AnalyticsReport:
    """Comprehensive context usage analytics report."""
    total_prompts_assembled: int = 0
    total_compressions: int = 0
    total_injections: int = 0
    total_tokens_consumed: int = 0
    tokens_by_source: dict[str, int] = field(default_factory=dict)
    average_compression_ratio: float = 0.0
    average_quality_score: float = 0.0
    average_injection_relevance: float = 0.0
    context_efficiency: float = 0.0
    window_overflow_events: int = 0
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_prompts_assembled": self.total_prompts_assembled,
            "total_compressions": self.total_compressions,
            "total_injections": self.total_injections,
            "total_tokens_consumed": self.total_tokens_consumed,
            "tokens_by_source": self.tokens_by_source,
            "average_compression_ratio": round(self.average_compression_ratio, 2),
            "average_quality_score": round(self.average_quality_score, 2),
            "average_injection_relevance": round(self.average_injection_relevance, 2),
            "context_efficiency": round(self.context_efficiency, 2),
            "window_overflow_events": self.window_overflow_events,
            "generated_at": self.generated_at,
        }


# ══════════════════════════════════════════════════════════════
# ContextAssembler
# ══════════════════════════════════════════════════════════════


class ContextAssembler:
    """Builds optimal context for agent prompts from multiple sources.

    Gathers context elements from system prompts, conversation history,
    memories, tools, knowledge graph, and persona. Allocates token budget
    based on priority and assembles a final context payload.

    Usage:
        assembler = ContextAssembler(model_token_limit=8192)
        context = assembler.assemble(
            system_prompt="You are a helpful assistant.",
            conversation=recent_messages,
            memories=recalled_memories,
            tools=available_tools,
        )
    """

    # Default priority ordering for source allocation
    PRIORITY_ORDER: list[tuple[ContextSource, ContextPriority]] = [
        (ContextSource.SYSTEM_PROMPT, ContextPriority.CRITICAL),
        (ContextSource.PERSONA, ContextPriority.CRITICAL),
        (ContextSource.CONVERSATION_HISTORY, ContextPriority.HIGH),
        (ContextSource.MEMORY, ContextPriority.HIGH),
        (ContextSource.TOOLS, ContextPriority.MEDIUM),
        (ContextSource.KNOWLEDGE_GRAPH, ContextPriority.MEDIUM),
    ]

    def __init__(self, model_token_limit: int = 8192):
        self.model_token_limit = model_token_limit
        self._budget = ContextBudget(total_tokens=model_token_limit)
        self._assemble_count = 0

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimation: approximately 4 characters per token."""
        if not text:
            return 0
        return max(1, len(text) // 4)

    def estimate_tokens_for_messages(self, messages: list[dict]) -> int:
        """Estimate total tokens for a list of chat messages."""
        total = 0
        for msg in messages:
            content = str(msg.get("content", ""))
            total += self.estimate_tokens(content)
            total += 4  # Role and formatting overhead per message
        return total

    def dynamic_window_size(self) -> int:
        """Determine the current context window size based on model limits."""
        return self.model_token_limit

    def assemble(
        self,
        system_prompt: str = "",
        conversation: list[dict] | None = None,
        memories: list[dict] | None = None,
        tools: list[dict] | None = None,
        knowledge: list[dict] | None = None,
        persona_context: str = "",
        max_tokens: int | None = None,
    ) -> list[ContextElement]:
        """Assemble context from all available sources into a token-budgeted list.

        Args:
            system_prompt: The base system prompt for the agent.
            conversation: Recent conversation messages.
            memories: Recalled memory entries.
            tools: Available tool definitions.
            knowledge: Knowledge graph results.
            persona_context: Active persona description.
            max_tokens: Override the token limit.

        Returns:
            A list of ContextElement objects sorted by priority.
        """
        conversation = conversation or []
        memories = memories or []
        tools = tools or []
        knowledge = knowledge or []

        if max_tokens is not None:
            self._budget = ContextBudget(total_tokens=max_tokens)
        else:
            self._budget = ContextBudget(total_tokens=self.model_token_limit)

        elements: list[ContextElement] = []

        # System prompt (critical priority)
        if system_prompt:
            element = self._create_element(
                source=ContextSource.SYSTEM_PROMPT,
                content=system_prompt,
                priority=ContextPriority.CRITICAL,
                importance_score=1.0,
            )
            elements.append(element)

        # Persona context (critical priority)
        if persona_context:
            element = self._create_element(
                source=ContextSource.PERSONA,
                content=persona_context,
                priority=ContextPriority.CRITICAL,
                importance_score=0.95,
            )
            elements.append(element)

        # Conversation history (high priority, paginated)
        for msg in conversation:
            content = str(msg.get("content", ""))
            role = msg.get("role", "unknown")
            importance = 0.8 if role == "user" else 0.6
            element = self._create_element(
                source=ContextSource.CONVERSATION_HISTORY,
                content=content,
                priority=ContextPriority.HIGH,
                importance_score=importance,
                metadata={"role": role},
            )
            elements.append(element)

        # Memory entries (high priority)
        for mem in memories:
            content = mem.get("content", "")
            importance = float(mem.get("importance", 0.5))
            element = self._create_element(
                source=ContextSource.MEMORY,
                content=content,
                priority=ContextPriority.HIGH,
                importance_score=importance,
                metadata={"memory_id": mem.get("id", ""), "memory_type": mem.get("memory_type", "")},
            )
            elements.append(element)

        # Tool definitions (medium priority)
        for tool in tools:
            content = tool.get("description", "") or tool.get("name", "")
            element = self._create_element(
                source=ContextSource.TOOLS,
                content=content,
                priority=ContextPriority.MEDIUM,
                importance_score=0.5,
                metadata={"tool_name": tool.get("name", "")},
            )
            elements.append(element)

        # Knowledge graph entries (medium priority)
        for kg_entry in knowledge:
            content = kg_entry.get("content", "") or kg_entry.get("summary", "")
            element = self._create_element(
                source=ContextSource.KNOWLEDGE_GRAPH,
                content=content,
                priority=ContextPriority.MEDIUM,
                importance_score=0.4,
                metadata={"entity": kg_entry.get("entity", ""), "relation": kg_entry.get("relation", "")},
            )
            elements.append(element)

        # Apply token budget: sort by priority then importance, trim to fit
        elements = self._apply_budget(elements)

        self._assemble_count += 1
        logger.info(
            f"Assembled context: {len(elements)} elements, "
            f"{sum(e.token_count for e in elements)} estimated tokens"
        )

        return elements

    def _create_element(
        self,
        source: ContextSource,
        content: str,
        priority: ContextPriority,
        importance_score: float = 0.5,
        metadata: dict[str, Any] | None = None,
    ) -> ContextElement:
        """Create a ContextElement with computed token count."""
        return ContextElement(
            source=source,
            content=content,
            token_count=self.estimate_tokens(content),
            priority=priority,
            importance_score=importance_score,
            metadata=metadata or {},
        )

    def _apply_budget(self, elements: list[ContextElement]) -> list[ContextElement]:
        """Apply token budget by trimming lowest-priority elements first."""
        priority_order = {
            ContextPriority.CRITICAL: 0,
            ContextPriority.HIGH: 1,
            ContextPriority.MEDIUM: 2,
            ContextPriority.LOW: 3,
        }

        # Sort: critical first, then high, etc. Within same priority, higher importance first
        elements.sort(
            key=lambda e: (priority_order.get(e.priority, 99), -e.importance_score)
        )

        result: list[ContextElement] = []
        tokens_used = 0

        for element in elements:
            if tokens_used + element.token_count <= self._budget.total_tokens:
                result.append(element)
                tokens_used += element.token_count
            else:
                # Try to chunk the element if it's conversation history
                if element.source == ContextSource.CONVERSATION_HISTORY:
                    remaining = self._budget.total_tokens - tokens_used
                    if remaining > 50:
                        chunked_content = element.content[: remaining * 4]
                        element.content = chunked_content + "..."
                        element.token_count = self.estimate_tokens(element.content)
                        result.append(element)
                        tokens_used += element.token_count
                break

        self._budget.used_tokens = tokens_used
        return result

    def chunk_conversation(self, messages: list[dict], chunk_size: int = 20) -> list[list[dict]]:
        """Split conversation into manageable chunks for pagination."""
        chunks = []
        for i in range(0, len(messages), chunk_size):
            chunks.append(messages[i : i + chunk_size])
        return chunks

    def get_budget(self) -> ContextBudget:
        """Get the current token budget state."""
        return self._budget

    def get_stats(self) -> dict[str, Any]:
        return {
            "model_token_limit": self.model_token_limit,
            "budget_used": self._budget.used_tokens,
            "budget_total": self._budget.total_tokens,
            "assemblies_performed": self._assemble_count,
        }


# ══════════════════════════════════════════════════════════════
# ContextCompressor
# ══════════════════════════════════════════════════════════════


class ContextCompressor:
    """Compresses context to fit within token limits.

    Applies summarization, entity extraction, and truncation strategies
    to reduce context size while preserving key information. Uses
    importance scoring to decide what to keep and what to compress.

    Usage:
        compressor = ContextCompressor(threshold_tokens=4096)
        result = compressor.compress(elements, strategy=CompressionStrategy.HYBRID)
    """

    # Minimum tokens to trigger compression
    DEFAULT_COMPRESSION_THRESHOLD = 4096

    # Maximum summary length as a fraction of original
    DEFAULT_SUMMARY_RATIO = 0.3

    def __init__(
        self,
        threshold_tokens: int = DEFAULT_COMPRESSION_THRESHOLD,
        summary_ratio: float = DEFAULT_SUMMARY_RATIO,
    ):
        self.threshold_tokens = threshold_tokens
        self.summary_ratio = summary_ratio
        self._compression_count = 0
        self._total_original_tokens = 0
        self._total_compressed_tokens = 0

    def estimate_tokens(self, text: str) -> int:
        if not text:
            return 0
        return max(1, len(text) // 4)

    def compress(
        self,
        elements: list[ContextElement],
        strategy: CompressionStrategy = CompressionStrategy.HYBRID,
        preserve_action_items: bool = True,
        preserve_decisions: bool = True,
    ) -> CompressionResult:
        """Compress a list of context elements to fit within the threshold.

        Args:
            elements: Context elements to compress.
            strategy: Compression strategy to apply.
            preserve_action_items: Keep action items and todos intact.
            preserve_decisions: Keep decision records intact.

        Returns:
            CompressionResult with the compressed content and metrics.
        """
        total_input_tokens = sum(e.token_count for e in elements)

        if total_input_tokens <= self.threshold_tokens:
            return CompressionResult(
                original_tokens=total_input_tokens,
                compressed_tokens=total_input_tokens,
                compression_ratio=1.0,
                strategy_used=strategy,
                quality_score=1.0,
            )

        result = CompressionResult(
            original_tokens=total_input_tokens,
            strategy_used=strategy,
        )

        if strategy == CompressionStrategy.SUMMARIZATION:
            result = self._compress_by_summarization(elements, result, preserve_action_items, preserve_decisions)
        elif strategy == CompressionStrategy.ENTITY_EXTRACTION:
            result = self._compress_by_entity_extraction(elements, result)
        elif strategy == CompressionStrategy.TRUNCATION:
            result = self._compress_by_truncation(elements, result)
        else:  # HYBRID
            result = self._compress_hybrid(elements, result, preserve_action_items, preserve_decisions)

        # Compute final metrics
        result.compressed_tokens = self.estimate_tokens(result.summary)
        if result.original_tokens > 0:
            result.compression_ratio = result.original_tokens / max(result.compressed_tokens, 1)
        result.quality_score = self._calculate_quality(elements, result)

        self._compression_count += 1
        self._total_original_tokens += total_input_tokens
        self._total_compressed_tokens += result.compressed_tokens

        logger.info(
            f"Compressed {total_input_tokens} -> {result.compressed_tokens} tokens "
            f"({result.compression_ratio:.1f}x, strategy={strategy.value})"
        )

        return result

    def _compress_by_summarization(
        self,
        elements: list[ContextElement],
        result: CompressionResult,
        preserve_action_items: bool,
        preserve_decisions: bool,
    ) -> CompressionResult:
        """Summarize context by extracting key sentences and patterns."""
        summary_parts: list[str] = []
        key_points: list[str] = []
        entities: list[dict[str, Any]] = []

        # Sort by importance, process high-importance elements first
        sorted_elements = sorted(elements, key=lambda e: -e.importance_score)

        for element in sorted_elements:
            content = element.content

            # Extract entities (proper nouns, capitalized terms)
            extracted = self._extract_entities(content)
            entities.extend(extracted)

            # Extract key sentences based on importance
            sentences = self._split_sentences(content)
            for sentence in sentences:
                if self._is_key_sentence(sentence, preserve_action_items, preserve_decisions):
                    key_points.append(sentence[:200])

            # Build summary from element source and first meaningful content
            if element.source == ContextSource.CONVERSATION_HISTORY:
                role = element.metadata.get("role", "")
                preview = content[:150].replace("\n", " ")
                summary_parts.append(f"[{role}]: {preview}")
            elif element.source == ContextSource.MEMORY:
                summary_parts.append(content[:200])
            elif element.source == ContextSource.KNOWLEDGE_GRAPH:
                summary_parts.append(content[:150])

        # Deduplicate key points
        unique_points = list(dict.fromkeys(key_points))

        result.summary = "\n".join(summary_parts[:20])
        result.key_points = unique_points[:15]
        result.extracted_entities = entities[:20]

        # Calculate importance distribution
        result.importance_distribution = self._compute_importance_distribution(elements)

        return result

    def _compress_by_entity_extraction(
        self,
        elements: list[ContextElement],
        result: CompressionResult,
    ) -> CompressionResult:
        """Compress by extracting entities and relationships only."""
        all_entities: list[dict[str, Any]] = []
        all_content = ""

        for element in elements:
            all_content += element.content + " "
            entities = self._extract_entities(element.content)
            all_entities.extend(entities)

        # Deduplicate entities by name
        seen: set[str] = set()
        unique_entities = []
        for entity in all_entities:
            name = entity.get("name", "")
            if name and name not in seen:
                seen.add(name)
                unique_entities.append(entity)

        result.extracted_entities = unique_entities[:30]
        result.summary = f"Entities: {', '.join(e.get('name', '') for e in unique_entities[:20])}"
        result.key_points = [
            f"{e.get('name', '')} ({e.get('type', 'unknown')})" for e in unique_entities[:10]
        ]

        return result

    def _compress_by_truncation(
        self,
        elements: list[ContextElement],
        result: CompressionResult,
    ) -> CompressionResult:
        """Simple truncation: keep highest-importance elements until budget is met."""
        sorted_elements = sorted(elements, key=lambda e: -e.importance_score)
        kept_content: list[str] = []
        tokens_used = 0

        for element in sorted_elements:
            if tokens_used >= self.threshold_tokens:
                break
            chars_to_take = min(len(element.content), (self.threshold_tokens - tokens_used) * 4)
            kept_content.append(element.content[:chars_to_take])
            tokens_used += self.estimate_tokens(element.content[:chars_to_take])

        result.summary = "\n".join(kept_content)
        result.compression_ratio = (
            result.original_tokens / max(self.estimate_tokens(result.summary), 1)
        )
        return result

    def _compress_hybrid(
        self,
        elements: list[ContextElement],
        result: CompressionResult,
        preserve_action_items: bool,
        preserve_decisions: bool,
    ) -> CompressionResult:
        """Hybrid compression: summarize low-importance, keep high-importance intact."""
        critical_elements = [e for e in elements if e.priority == ContextPriority.CRITICAL]
        high_elements = [e for e in elements if e.priority == ContextPriority.HIGH]
        medium_elements = [e for e in elements if e.priority == ContextPriority.MEDIUM]
        low_elements = [e for e in elements if e.priority == ContextPriority.LOW]

        summary_parts: list[str] = []
        key_points: list[str] = []
        entities: list[dict[str, Any]] = []

        # Keep critical elements as-is
        for e in critical_elements:
            summary_parts.append(e.content)

        # Lightly summarize high-priority elements
        for e in high_elements:
            sentences = self._split_sentences(e.content)
            important = [s for s in sentences if self._is_key_sentence(s, preserve_action_items, preserve_decisions)]
            if important:
                summary_parts.append(" ".join(important[:3]))
            else:
                summary_parts.append(e.content[:200])

        # Summarize medium and low priority
        for e in medium_elements + low_elements:
            key_points.append(e.content[:200])
            entities.extend(self._extract_entities(e.content))

        result.summary = "\n".join(summary_parts[:30])
        result.key_points = list(dict.fromkeys(key_points))[:10]
        result.extracted_entities = entities[:15]
        result.importance_distribution = self._compute_importance_distribution(elements)

        return result

    def _extract_entities(self, text: str) -> list[dict[str, Any]]:
        """Extract named entities and key terms from text."""
        entities: list[dict[str, Any]] = []

        # Extract capitalized multi-word phrases (likely proper nouns)
        capitalized_pattern = re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b')
        for match in capitalized_pattern.finditer(text):
            entities.append({
                "name": match.group(1),
                "type": "proper_noun",
                "position": match.start(),
            })

        # Extract single capitalized words (names, tools, concepts)
        single_cap_pattern = re.compile(r'\b([A-Z][a-zA-Z]{2,})\b')
        seen_names = {e["name"] for e in entities}
        for match in single_cap_pattern.finditer(text):
            name = match.group(1)
            if name not in seen_names and name.lower() not in {
                "The", "This", "That", "These", "Those", "There", "They",
                "When", "Where", "What", "Which", "Would", "Could", "Should",
            }:
                entities.append({
                    "name": name,
                    "type": "term",
                    "position": match.start(),
                })
                seen_names.add(name)

        return entities

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _is_key_sentence(
        self,
        sentence: str,
        preserve_action_items: bool,
        preserve_decisions: bool,
    ) -> bool:
        """Check if a sentence contains key information worth preserving."""
        lower = sentence.lower()

        # Always preserve action items and todos
        if preserve_action_items:
            action_indicators = [
                "todo", "to do", "action item", "next step", "follow up",
                "need to", "must", "should", "will", "going to", "plan to",
                "task:", "action:", "step:",
            ]
            if any(indicator in lower for indicator in action_indicators):
                return True

        # Preserve decisions
        if preserve_decisions:
            decision_indicators = [
                "decided", "decision", "choose", "chose", "selected",
                "agreed", "confirmed", "final", "conclusion",
            ]
            if any(indicator in lower for indicator in decision_indicators):
                return True

        # Preserve sentences with specific information
        info_indicators = [
            "important", "critical", "key", "note:", "remember",
            "preference", "prefer", "favorite", "always", "never",
        ]
        if any(indicator in lower for indicator in info_indicators):
            return True

        return False

    def _compute_importance_distribution(
        self,
        elements: list[ContextElement],
    ) -> dict[str, float]:
        """Compute the distribution of importance scores across sources."""
        distribution: dict[str, list[float]] = {}
        for e in elements:
            source_key = e.source.value
            if source_key not in distribution:
                distribution[source_key] = []
            distribution[source_key].append(e.importance_score)

        return {
            source: sum(scores) / len(scores)
            for source, scores in distribution.items()
        }

    def _calculate_quality(
        self,
        original_elements: list[ContextElement],
        result: CompressionResult,
    ) -> float:
        """Calculate a quality score for the compression result."""
        score = 0.5

        # Bonus for having extracted entities
        if result.extracted_entities:
            score += 0.15

        # Bonus for having key points
        if result.key_points:
            score += 0.15

        # Bonus for reasonable compression ratio
        if 2.0 <= result.compression_ratio <= 20.0:
            score += 0.10

        # Bonus for having a meaningful summary
        if result.summary and len(result.summary) > 50:
            score += 0.10

        return min(max(score, 0.0), 1.0)

    def get_compression_ratio(self) -> float:
        """Get the overall compression ratio across all compressions."""
        if self._total_compressed_tokens == 0:
            return 1.0
        return self._total_original_tokens / self._total_compressed_tokens

    def get_stats(self) -> dict[str, Any]:
        return {
            "threshold_tokens": self.threshold_tokens,
            "summary_ratio": self.summary_ratio,
            "compressions_performed": self._compression_count,
            "total_original_tokens": self._total_original_tokens,
            "total_compressed_tokens": self._total_compressed_tokens,
            "overall_compression_ratio": round(self.get_compression_ratio(), 2),
        }


# ══════════════════════════════════════════════════════════════
# ContextInjector
# ══════════════════════════════════════════════════════════════


class ContextInjector:
    """Injects relevant context into agent prompts dynamically.

    Scores context elements for relevance to the current task, then
    injects the most relevant elements into a prompt template using
    variable substitution and multi-turn context tracking.

    Usage:
        injector = ContextInjector()
        result = injector.inject(
            template="You are {persona}. Context: {memory}. {conversation}",
            elements=assembled_context,
            task_description="Debug the authentication module",
        )
    """

    # Template variable markers
    TEMPLATE_PATTERN = re.compile(r'\{(\w+)\}')

    def __init__(self):
        self._injection_count = 0
        self._context_tracker: dict[str, list[str]] = {}
        self._total_relevance_sum = 0.0
        self._relevance_count = 0

    def score_relevance(self, element: ContextElement, task_description: str) -> float:
        """Score how relevant a context element is to the current task.

        Uses keyword overlap and semantic similarity heuristics to compute
        a relevance score between 0.0 and 1.0.
        """
        if not task_description:
            return element.importance_score

        task_lower = task_description.lower()
        content_lower = element.content.lower()

        # Extract task keywords
        task_keywords = set(task_lower.split())

        # Count keyword overlap
        content_words = set(content_lower.split())
        overlap = task_keywords & content_words
        overlap_score = len(overlap) / max(len(task_keywords), 1)

        # Boost for exact phrase matches
        phrase_boost = 0.0
        task_phrases = self._extract_phrases(task_lower)
        for phrase in task_phrases:
            if phrase in content_lower:
                phrase_boost += 0.15

        # Combine scores
        relevance = (overlap_score * 0.6) + (element.importance_score * 0.3) + min(phrase_boost, 0.1)

        return min(max(relevance, 0.0), 1.0)

    def _extract_phrases(self, text: str) -> list[str]:
        """Extract meaningful multi-word phrases from text."""
        words = text.split()
        phrases = []
        for i in range(len(words) - 1):
            phrases.append(f"{words[i]} {words[i + 1]}")
        return phrases

    def inject(
        self,
        template: str,
        elements: list[ContextElement],
        task_description: str = "",
        variables: dict[str, str] | None = None,
    ) -> InjectResult:
        """Inject the most relevant context elements into a prompt template.

        Args:
            template: Prompt template with {variable} placeholders.
            elements: Assembled context elements to choose from.
            task_description: Current task for relevance scoring.
            variables: Additional template variables to substitute.

        Returns:
            InjectResult with injection metrics and the filled template.
        """
        variables = variables or {}
        result = InjectResult()
        start_time = datetime.now(timezone.utc)

        # Score relevance for each element
        scored_elements: list[tuple[float, ContextElement]] = []
        for element in elements:
            score = self.score_relevance(element, task_description)
            scored_elements.append((score, element))
            result.relevance_scores[element.id] = round(score, 3)

        # Sort by relevance, highest first
        scored_elements.sort(key=lambda x: -x[0])

        # Group elements by source for template filling
        source_groups: dict[str, list[ContextElement]] = {}
        for score, element in scored_elements:
            source_key = element.source.value
            if source_key not in source_groups:
                source_groups[source_key] = []
            source_groups[source_key].append(element)

        # Build variable substitutions
        substitutions: dict[str, str] = dict(variables)

        # Map sources to template variables
        source_mappings = {
            "system_prompt": "system_prompt",
            "conversation_history": "conversation",
            "memory": "memory",
            "tools": "tools",
            "knowledge_graph": "knowledge",
            "persona": "persona",
        }

        for source_key, elements_in_source in source_groups.items():
            var_name = source_mappings.get(source_key, source_key)
            top_elements = elements_in_source[:5]  # Take top 5 most relevant
            combined = "\n".join(e.content for e in top_elements)
            substitutions[var_name] = combined

        # Fill the template
        filled = template
        for var_name, value in substitutions.items():
            filled = filled.replace(f"{{{var_name}}}", value)

        # Track injected elements for multi-turn context
        injected_ids = [e.id for _, e in scored_elements[:10]]
        session_key = task_description[:50] if task_description else "default"
        if session_key not in self._context_tracker:
            self._context_tracker[session_key] = []
        self._context_tracker[session_key].extend(injected_ids)

        # Compute metrics
        result.elements_injected = len(scored_elements)
        result.tokens_injected = sum(e.token_count for _, e in scored_elements)
        result.sources_used = [
            s for s in ContextSource if s.value in source_groups
        ]
        result.template_variables = substitutions
        result.injection_latency_ms = (
            datetime.now(timezone.utc) - start_time
        ).total_seconds() * 1000

        # Track overall relevance
        if scored_elements:
            avg_relevance = sum(s for s, _ in scored_elements) / len(scored_elements)
            self._total_relevance_sum += avg_relevance
            self._relevance_count += 1

        self._injection_count += 1
        logger.info(
            f"Injected {len(scored_elements)} elements into prompt "
            f"({result.tokens_injected} tokens, {result.injection_latency_ms:.1f}ms)"
        )

        return result

    def get_multi_turn_context(self, session_key: str, limit: int = 20) -> list[str]:
        """Get previously injected element IDs for multi-turn tracking."""
        return self._context_tracker.get(session_key, [])[-limit:]

    def clear_multi_turn_context(self, session_key: str):
        """Clear tracked context for a session."""
        self._context_tracker.pop(session_key, None)

    def get_average_relevance(self) -> float:
        """Get the average relevance score across all injections."""
        if self._relevance_count == 0:
            return 0.0
        return self._total_relevance_sum / self._relevance_count

    def get_stats(self) -> dict[str, Any]:
        return {
            "injections_performed": self._injection_count,
            "average_relevance": round(self.get_average_relevance(), 3),
            "tracked_sessions": len(self._context_tracker),
            "total_tracked_elements": sum(len(v) for v in self._context_tracker.values()),
        }


# ══════════════════════════════════════════════════════════════
# ContextWindow
# ══════════════════════════════════════════════════════════════


class ContextWindow:
    """Manages the sliding context window for agent conversations.

    Maintains a bounded window of context elements with aging, prioritization,
    and overflow handling. Older or lower-priority elements are evicted when
    the window exceeds capacity.

    Usage:
        window = ContextWindow(max_tokens=8192, max_elements=100)
        window.add(element)
        window.evict_oldest()
        snapshot = window.snapshot()
    """

    def __init__(self, max_tokens: int = 8192, max_elements: int = 100):
        self.max_tokens = max_tokens
        self.max_elements = max_elements
        self._elements: deque[ContextElement] = deque()
        self._overflow_count = 0
        self._total_token_usage = 0
        self._refresh_trigger_count = 0

    def estimate_tokens(self, text: str) -> int:
        if not text:
            return 0
        return max(1, len(text) // 4)

    @property
    def total_tokens(self) -> int:
        return sum(e.token_count for e in self._elements)

    @property
    def element_count(self) -> int:
        return len(self._elements)

    @property
    def is_overfull(self) -> bool:
        return self.total_tokens > self.max_tokens or self.element_count > self.max_elements

    def add(self, element: ContextElement):
        """Add an element to the context window."""
        self._elements.append(element)
        self._total_token_usage += element.token_count

        # Handle overflow
        while self.is_overfull:
            self._handle_overflow()

    def add_batch(self, elements: list[ContextElement]):
        """Add multiple elements to the context window."""
        for element in elements:
            self.add(element)

    def evict_oldest(self, count: int = 1) -> list[ContextElement]:
        """Evict the oldest elements from the window."""
        evicted = []
        for _ in range(min(count, len(self._elements))):
            if self._elements:
                evicted.append(self._elements.popleft())
        return evicted

    def evict_low_priority(self, count: int = 1) -> list[ContextElement]:
        """Evict the lowest-priority elements from the window."""
        priority_order = {
            ContextPriority.CRITICAL: 0,
            ContextPriority.HIGH: 1,
            ContextPriority.MEDIUM: 2,
            ContextPriority.LOW: 3,
        }

        sorted_indices = sorted(
            range(len(self._elements)),
            key=lambda i: (priority_order.get(self._elements[i].priority, 99), -self._elements[i].importance_score),
            reverse=True,
        )

        evicted = []
        for idx in sorted_indices[:count]:
            if idx < len(self._elements):
                evicted_element = self._elements[idx]
                evicted.append(evicted_element)
                # Mark for removal
                self._elements[idx] = None  # type: ignore

        # Clean up None entries
        self._elements = deque(e for e in self._elements if e is not None)

        return evicted

    def age_elements(self, age_threshold_seconds: float = 3600.0):
        """Age out elements older than the threshold."""
        now = datetime.now(timezone.utc)
        aged_out = []

        remaining = deque()
        for element in self._elements:
            try:
                created = datetime.fromisoformat(element.created_at)
                age = (now - created).total_seconds()
                if age > age_threshold_seconds:
                    aged_out.append(element)
                else:
                    remaining.append(element)
            except (ValueError, TypeError):
                remaining.append(element)

        self._elements = remaining
        if aged_out:
            logger.info(f"Aged out {len(aged_out)} elements from context window")

    def prioritize(self, element_id: str):
        """Boost the priority of a specific element in the window."""
        for element in self._elements:
            if element.id == element_id:
                element.importance_score = min(1.0, element.importance_score + 0.2)
                if element.priority == ContextPriority.LOW:
                    element.priority = ContextPriority.MEDIUM
                elif element.priority == ContextPriority.MEDIUM:
                    element.priority = ContextPriority.HIGH
                break

    def refresh(self):
        """Trigger a context refresh, evicting aged low-priority elements."""
        self.age_elements(age_threshold_seconds=1800.0)
        self._refresh_trigger_count += 1

        # If still overfull after aging, evict by priority
        while self.is_overfull:
            evicted = self.evict_low_priority(count=1)
            if not evicted:
                evicted = self.evict_oldest(count=1)
                if not evicted:
                    break

    def _handle_overflow(self):
        """Handle overflow by evicting the lowest-priority element."""
        self._overflow_count += 1

        # Try low-priority eviction first
        evicted = self.evict_low_priority(count=1)
        if not evicted:
            # Fall back to oldest eviction
            evicted = self.evict_oldest(count=1)

        if evicted:
            logger.debug(f"Context overflow: evicted element {evicted[0].id}")

    def get_element_by_id(self, element_id: str) -> ContextElement | None:
        for element in self._elements:
            if element.id == element_id:
                return element
        return None

    def get_elements_by_source(self, source: ContextSource) -> list[ContextElement]:
        return [e for e in self._elements if e.source == source]

    def snapshot(self) -> WindowSnapshot:
        """Create a snapshot of the current window state."""
        now = datetime.now(timezone.utc)
        ages = []

        source_dist: dict[str, int] = {}
        for element in self._elements:
            source_key = element.source.value
            source_dist[source_key] = source_dist.get(source_key, 0) + 1
            try:
                created = datetime.fromisoformat(element.created_at)
                ages.append((now - created).total_seconds())
            except (ValueError, TypeError):
                pass

        return WindowSnapshot(
            window_id=str(uuid.uuid4())[:8],
            total_elements=self.element_count,
            total_tokens=self.total_tokens,
            oldest_element_age=max(ages) if ages else 0.0,
            newest_element_age=min(ages) if ages else 0.0,
            source_distribution=source_dist,
            is_overfull=self.is_overfull,
            overflow_count=self._overflow_count,
            snapshot_time=now.isoformat(),
        )

    def clear(self):
        """Clear all elements from the window."""
        self._elements.clear()
        self._overflow_count = 0

    def get_stats(self) -> dict[str, Any]:
        return {
            "max_tokens": self.max_tokens,
            "max_elements": self.max_elements,
            "current_elements": self.element_count,
            "current_tokens": self.total_tokens,
            "is_overfull": self.is_overfull,
            "overflow_events": self._overflow_count,
            "refresh_triggers": self._refresh_trigger_count,
            "total_token_usage": self._total_token_usage,
        }


# ══════════════════════════════════════════════════════════════
# ContextAnalytics
# ══════════════════════════════════════════════════════════════


class ContextAnalytics:
    """Tracks and reports context usage metrics and efficiency.

    Collects data on token consumption by source, compression ratios,
    injection relevance, and overall context efficiency. Generates
    periodic reports for monitoring and optimization.

    Usage:
        analytics = ContextAnalytics()
        analytics.record_assembly(tokens_by_source)
        analytics.record_compression(original, compressed)
        report = analytics.generate_report()
    """

    def __init__(self):
        self._prompts_assembled = 0
        self._compressions_recorded = 0
        self._injections_recorded = 0
        self._total_tokens_consumed = 0
        self._tokens_by_source: dict[str, int] = {}
        self._compression_ratios: list[float] = []
        self._quality_scores: list[float] = []
        self._relevance_scores: list[float] = []
        self._overflow_events = 0
        self._efficiency_snapshots: list[float] = []

    def record_assembly(self, tokens_by_source: dict[str, int]):
        """Record token usage from a context assembly operation."""
        self._prompts_assembled += 1
        for source, tokens in tokens_by_source.items():
            self._tokens_by_source[source] = self._tokens_by_source.get(source, 0) + tokens
            self._total_tokens_consumed += tokens

    def record_compression(self, original_tokens: int, compressed_tokens: int, quality_score: float = 0.0):
        """Record metrics from a context compression operation."""
        self._compressions_recorded += 1
        if original_tokens > 0 and compressed_tokens > 0:
            ratio = original_tokens / compressed_tokens
            self._compression_ratios.append(ratio)
        self._quality_scores.append(quality_score)

    def record_injection(self, relevance_score: float):
        """Record relevance score from a context injection operation."""
        self._injections_recorded += 1
        self._relevance_scores.append(relevance_score)

    def record_overflow(self, count: int = 1):
        """Record context window overflow events."""
        self._overflow_events += count

    def record_efficiency(self, efficiency: float):
        """Record a context efficiency snapshot."""
        self._efficiency_snapshots.append(efficiency)

    def compute_efficiency(self) -> float:
        """Compute overall context efficiency.

        Efficiency is measured as the ratio of useful context tokens
        (those with high relevance) to total tokens consumed.
        """
        if self._total_tokens_consumed == 0:
            return 0.0

        avg_relevance = self.average_relevance()
        avg_compression = self.average_compression_ratio()

        # Efficiency = relevance * compression_efficiency / overflow_penalty
        overflow_penalty = 1.0 + (self._overflow_events * 0.01)
        efficiency = (avg_relevance * min(avg_compression, 10.0) / 10.0) / overflow_penalty

        return min(max(efficiency, 0.0), 1.0)

    def average_compression_ratio(self) -> float:
        if not self._compression_ratios:
            return 1.0
        return sum(self._compression_ratios) / len(self._compression_ratios)

    def average_quality_score(self) -> float:
        if not self._quality_scores:
            return 0.0
        return sum(self._quality_scores) / len(self._quality_scores)

    def average_relevance(self) -> float:
        if not self._relevance_scores:
            return 0.0
        return sum(self._relevance_scores) / len(self._relevance_scores)

    def generate_report(self) -> AnalyticsReport:
        """Generate a comprehensive analytics report."""
        return AnalyticsReport(
            total_prompts_assembled=self._prompts_assembled,
            total_compressions=self._compressions_recorded,
            total_injections=self._injections_recorded,
            total_tokens_consumed=self._total_tokens_consumed,
            tokens_by_source=dict(self._tokens_by_source),
            average_compression_ratio=self.average_compression_ratio(),
            average_quality_score=self.average_quality_score(),
            average_injection_relevance=self.average_relevance(),
            context_efficiency=self.compute_efficiency(),
            window_overflow_events=self._overflow_events,
        )

    def reset(self):
        """Reset all analytics counters."""
        self._prompts_assembled = 0
        self._compressions_recorded = 0
        self._injections_recorded = 0
        self._total_tokens_consumed = 0
        self._tokens_by_source = {}
        self._compression_ratios = []
        self._quality_scores = []
        self._relevance_scores = []
        self._overflow_events = 0
        self._efficiency_snapshots = []

    def get_stats(self) -> dict[str, Any]:
        return self.generate_report().to_dict()


# ══════════════════════════════════════════════════════════════
# ContextEngine
# ══════════════════════════════════════════════════════════════


class ContextEngine:
    """Orchestrates all context management components.

    Provides a unified interface for context assembly, compression,
    injection, window management, and analytics. Ties together the
    individual components into a cohesive pipeline.

    Usage:
        engine = ContextEngine(model_token_limit=8192)

        # Assemble context from sources
        elements = engine.assembler.assemble(
            system_prompt="You are a helpful AI.",
            conversation=recent_messages,
            memories=recalled,
        )

        # Add to the sliding window
        engine.window.add_batch(elements)

        # Compress if overfull
        if engine.window.is_overfull:
            result = engine.compressor.compress(
                list(engine.window._elements),
                strategy=CompressionStrategy.HYBRID,
            )

        # Inject into prompt
        inject_result = engine.injector.inject(
            template="System: {system_prompt}\n\nContext: {memory}\n\n{prompt}",
            elements=elements,
            task_description="Write a test",
        )

        # Get analytics
        report = engine.analytics.generate_report()
    """

    def __init__(self, model_token_limit: int = 8192):
        self.assembler = ContextAssembler(model_token_limit=model_token_limit)
        self.compressor = ContextCompressor(threshold_tokens=model_token_limit // 2)
        self.injector = ContextInjector()
        self.window = ContextWindow(max_tokens=model_token_limit)
        self.analytics = ContextAnalytics()

    def process_context(
        self,
        system_prompt: str = "",
        conversation: list[dict] | None = None,
        memories: list[dict] | None = None,
        tools: list[dict] | None = None,
        knowledge: list[dict] | None = None,
        persona_context: str = "",
        task_description: str = "",
        prompt_template: str = "{system_prompt}\n\n{memory}\n\n{prompt}",
        auto_compress: bool = True,
    ) -> dict[str, Any]:
        """Run the complete context processing pipeline.

        Assembles context from sources, manages the sliding window,
        optionally compresses overflow, and injects into a prompt template.

        Args:
            system_prompt: Base system prompt for the agent.
            conversation: Recent conversation messages.
            memories: Recalled memory entries.
            tools: Available tool definitions.
            knowledge: Knowledge graph results.
            persona_context: Active persona description.
            task_description: Description of the current task.
            prompt_template: Template for the final prompt with {variable} placeholders.
            auto_compress: Whether to automatically compress when overfull.

        Returns:
            Dictionary with assembled elements, compression result (if any),
            injection result, and window snapshot.
        """
        conversation = conversation or []

        # 1. Assemble context
        elements = self.assembler.assemble(
            system_prompt=system_prompt,
            conversation=conversation,
            memories=memories,
            tools=tools,
            knowledge=knowledge,
            persona_context=persona_context,
        )

        # 2. Track assembly tokens
        tokens_by_source: dict[str, int] = {}
        for e in elements:
            src = e.source.value
            tokens_by_source[src] = tokens_by_source.get(src, 0) + e.token_count
        self.analytics.record_assembly(tokens_by_source)

        # 3. Add to sliding window
        self.window.add_batch(elements)

        # 4. Compress if needed
        compression_result = None
        if auto_compress and self.window.is_overfull:
            compression_result = self.compressor.compress(
                list(self.window._elements),
                strategy=CompressionStrategy.HYBRID,
            )
            self.analytics.record_compression(
                original_tokens=compression_result.original_tokens,
                compressed_tokens=compression_result.compressed_tokens,
                quality_score=compression_result.quality_score,
            )
            self.window.refresh()

        # 5. Inject into prompt
        inject_result = self.injector.inject(
            template=prompt_template,
            elements=elements,
            task_description=task_description,
        )
        self.analytics.record_injection(
            relevance_score=self.injector.get_average_relevance(),
        )

        # 6. Track overflow
        if self.window._overflow_count > 0:
            self.analytics.record_overflow(self.window._overflow_count)

        # 7. Compute and record efficiency
        efficiency = self.analytics.compute_efficiency()
        self.analytics.record_efficiency(efficiency)

        return {
            "elements": elements,
            "element_count": len(elements),
            "total_tokens": sum(e.token_count for e in elements),
            "compression": compression_result.to_dict() if compression_result else None,
            "injection": {
                "elements_injected": inject_result.elements_injected,
                "tokens_injected": inject_result.tokens_injected,
                "sources_used": [s.value for s in inject_result.sources_used],
                "latency_ms": inject_result.injection_latency_ms,
            },
            "window_snapshot": self.window.snapshot(),
            "efficiency": round(efficiency, 3),
        }

    def get_full_stats(self) -> dict[str, Any]:
        """Get comprehensive statistics from all components."""
        return {
            "assembler": self.assembler.get_stats(),
            "compressor": self.compressor.get_stats(),
            "injector": self.injector.get_stats(),
            "window": self.window.get_stats(),
            "analytics": self.analytics.get_stats(),
        }

    def reset(self):
        """Reset all components to their initial state."""
        self.window.clear()
        self.analytics.reset()
        self.injector._context_tracker.clear()
        self.injector._injection_count = 0
        self.injector._total_relevance_sum = 0.0
        self.injector._relevance_count = 0
        self.compressor._compression_count = 0
        self.compressor._total_original_tokens = 0
        self.compressor._total_compressed_tokens = 0
        self.assembler._assemble_count = 0
        self.assembler._budget = ContextBudget(total_tokens=self.assembler.model_token_limit)


# ══════════════════════════════════════════════════════════════
# Global Instance
# ══════════════════════════════════════════════════════════════

context_engine = ContextEngine()