"""Buddy Agent Knowledge Distiller - Knowledge Compression and Transfer Engine.

The distiller compresses complex learned knowledge into compact, transferable
forms. It extracts key patterns from experience data, distills them into
concise knowledge units, and supports transfer of distilled knowledge across
agents.

Core capabilities:
- Source registration from experience, observation, feedback, etc.
- Multi-level compression (light, moderate, aggressive, extreme)
- Key point extraction and cross-source pattern discovery
- Cross-agent knowledge transfer with acknowledgment tracking
- Keyword-based knowledge querying with relevance scoring
- Aggregate statistics and observability

Part of the AI-Native Buddy Agent system.
"""

from __future__ import annotations

import logging
import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("buddy.knowledge_distiller")


# ── Core Enums ────────────────────────────────────────────────────

class KnowledgeType(str, Enum):
    """Types of distilled knowledge."""
    FACTUAL = "factual"           # Verified factual information
    PROCEDURAL = "procedural"     # Step-by-step procedures
    CONCEPTUAL = "conceptual"     # Abstract concepts and ideas
    HEURISTIC = "heuristic"       # Rules of thumb
    PATTERN = "pattern"           # Observed recurring patterns
    RULE = "rule"                 # Strict, enforceable rules


class CompressionLevel(str, Enum):
    """Compression aggressiveness levels."""
    LIGHT = "light"               # Minimal compression, retain detail
    MODERATE = "moderate"         # Balanced compression
    AGGRESSIVE = "aggressive"     # Heavy compression
    EXTREME = "extreme"           # Maximum compression


class DistillationStatus(str, Enum):
    """Status of a distillation session."""
    PENDING = "pending"
    EXTRACTING = "extracting"
    COMPRESSING = "compressing"
    COMPLETED = "completed"
    FAILED = "failed"


class SourceType(str, Enum):
    """Types of knowledge sources."""
    EXPERIENCE = "experience"       # Direct agent experience
    OBSERVATION = "observation"     # Observed events
    FEEDBACK = "feedback"           # External feedback
    DOCUMENTATION = "documentation" # Reference documents
    INTERACTION = "interaction"     # User/system interactions


class TransferStatus(str, Enum):
    """Status of a cross-agent knowledge transfer."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"
    FAILED = "failed"


# ── Data Structures ───────────────────────────────────────────────

@dataclass
class KnowledgeSource:
    """A raw knowledge source awaiting distillation."""
    source_id: str
    source_type: SourceType
    agent_id: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    relevance_score: float = 0.5
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_type": self.source_type.value,
            "agent_id": self.agent_id,
            "content": self.content,
            "metadata": dict(self.metadata),
            "relevance_score": self.relevance_score,
            "created_at": self.created_at,
        }


@dataclass
class DistilledKnowledge:
    """A compressed knowledge unit derived from one or more sources."""
    knowledge_id: str
    source_ids: list[str] = field(default_factory=list)
    knowledge_type: KnowledgeType = KnowledgeType.FACTUAL
    title: str = ""
    summary: str = ""
    key_points: list[str] = field(default_factory=list)
    patterns: list[str] = field(default_factory=list)
    compression_level: CompressionLevel = CompressionLevel.MODERATE
    original_size: int = 0
    compressed_size: int = 0
    fidelity_score: float = 0.8
    tags: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    status: DistillationStatus = DistillationStatus.PENDING

    @property
    def compression_ratio(self) -> float:
        """Ratio of original to compressed size (higher = more compression)."""
        return self.original_size / max(self.compressed_size, 1)

    def to_dict(self) -> dict[str, Any]:
        return {
            "knowledge_id": self.knowledge_id,
            "source_ids": list(self.source_ids),
            "knowledge_type": self.knowledge_type.value,
            "title": self.title,
            "summary": self.summary,
            "key_points": list(self.key_points),
            "patterns": list(self.patterns),
            "compression_level": self.compression_level.value,
            "original_size": self.original_size,
            "compressed_size": self.compressed_size,
            "fidelity_score": self.fidelity_score,
            "tags": list(self.tags),
            "created_at": self.created_at,
            "status": self.status.value,
            "compression_ratio": self.compression_ratio,
        }


@dataclass
class DistillationSession:
    """A single distillation session tracking state transitions."""
    session_id: str
    agent_id: str
    source_ids: list[str] = field(default_factory=list)
    compression_level: CompressionLevel = CompressionLevel.MODERATE
    status: DistillationStatus = DistillationStatus.PENDING
    result_knowledge_id: str | None = None
    started_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "source_ids": list(self.source_ids),
            "compression_level": self.compression_level.value,
            "status": self.status.value,
            "result_knowledge_id": self.result_knowledge_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error": self.error,
        }


@dataclass
class KnowledgeTransfer:
    """A cross-agent knowledge transfer record."""
    transfer_id: str
    source_agent_id: str
    target_agent_id: str
    knowledge_id: str
    status: TransferStatus = TransferStatus.PENDING
    transferred_at: float | None = None
    acknowledged: bool = False
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "transfer_id": self.transfer_id,
            "source_agent_id": self.source_agent_id,
            "target_agent_id": self.target_agent_id,
            "knowledge_id": self.knowledge_id,
            "status": self.status.value,
            "transferred_at": self.transferred_at,
            "acknowledged": self.acknowledged,
            "notes": self.notes,
        }


@dataclass
class KnowledgeQuery:
    """A recorded knowledge query with matched results."""
    query_id: str
    agent_id: str
    query_text: str
    matched_knowledge_ids: list[str] = field(default_factory=list)
    top_score: float = 0.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query_id": self.query_id,
            "agent_id": self.agent_id,
            "query_text": self.query_text,
            "matched_knowledge_ids": list(self.matched_knowledge_ids),
            "top_score": self.top_score,
            "created_at": self.created_at,
        }


@dataclass
class DistillerStats:
    """Aggregate statistics about the distiller's activity."""
    total_sources: int = 0
    total_distilled: int = 0
    total_sessions: int = 0
    total_transfers: int = 0
    total_queries: int = 0
    avg_compression_ratio: float = 0.0
    avg_fidelity: float = 0.0
    distilled_by_type: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_sources": self.total_sources,
            "total_distilled": self.total_distilled,
            "total_sessions": self.total_sessions,
            "total_transfers": self.total_transfers,
            "total_queries": self.total_queries,
            "avg_compression_ratio": self.avg_compression_ratio,
            "avg_fidelity": self.avg_fidelity,
            "distilled_by_type": dict(self.distilled_by_type),
        }


# ── Compression Configuration ────────────────────────────────────

# Number of key points to retain per compression level.
_KEY_POINTS_BY_LEVEL: dict[CompressionLevel, int] = {
    CompressionLevel.LIGHT: 8,
    CompressionLevel.MODERATE: 5,
    CompressionLevel.AGGRESSIVE: 3,
    CompressionLevel.EXTREME: 1,
}

# Stopwords excluded from pattern extraction to avoid noisy common-words.
_STOPWORDS: frozenset[str] = frozenset({
    "the", "a", "an", "and", "or", "but", "if", "then", "else", "when",
    "at", "by", "for", "with", "about", "against", "between", "into",
    "through", "during", "before", "after", "above", "below", "to", "from",
    "up", "down", "in", "out", "on", "off", "over", "under", "again",
    "further", "is", "are", "was", "were", "be", "been", "being", "have",
    "has", "had", "do", "does", "did", "of", "as", "it", "its", "this",
    "that", "these", "those", "i", "you", "he", "she", "we", "they",
    "not", "no", "so", "than", "too", "very", "can", "will", "just",
})


class AgentKnowledgeDistiller:
    """Knowledge compression and transfer engine.

    The distiller performs three primary functions:
    1. Registers raw knowledge sources from various agent activities.
    2. Distills multiple sources into compact, transferable knowledge units
       by extracting key points, identifying cross-source patterns, and
       generating compressed summaries at configurable compression levels.
    3. Supports transferring distilled knowledge between agents with
       acknowledgment tracking.

    All state mutations are guarded by an internal lock, making the
    distiller safe to use from multiple threads.
    """

    MAX_SOURCES: int = 10_000
    MAX_KNOWLEDGE: int = 10_000
    MAX_QUERIES: int = 5_000

    def __init__(self) -> None:
        self._sources: dict[str, KnowledgeSource] = {}
        self._knowledge: dict[str, DistilledKnowledge] = {}
        self._sessions: dict[str, DistillationSession] = {}
        self._transfers: dict[str, KnowledgeTransfer] = {}
        self._queries: list[KnowledgeQuery] = []
        self._lock = threading.Lock()

    # ── Source Management ────────────────────────────────────────

    def register_source(
        self,
        source_type: SourceType,
        agent_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
        relevance_score: float = 0.5,
    ) -> KnowledgeSource:
        """Register a new knowledge source for future distillation.

        If the source registry is at capacity, the oldest source is evicted
        to make room for the new one. Relevance scores are clamped to [0, 1].
        """
        with self._lock:
            if len(self._sources) >= self.MAX_SOURCES:
                oldest_id = min(
                    self._sources.keys(),
                    key=lambda sid: self._sources[sid].created_at,
                )
                self._sources.pop(oldest_id, None)
                logger.debug(
                    "Evicted oldest source %s to respect MAX_SOURCES", oldest_id
                )

            source = KnowledgeSource(
                source_id=f"src_{uuid.uuid4().hex[:12]}",
                source_type=source_type,
                agent_id=agent_id,
                content=content,
                metadata=dict(metadata) if metadata else {},
                relevance_score=max(0.0, min(1.0, relevance_score)),
                created_at=time.time(),
            )
            self._sources[source.source_id] = source
            return source

    def get_source(self, source_id: str) -> KnowledgeSource | None:
        """Retrieve a single source by id."""
        with self._lock:
            return self._sources.get(source_id)

    def list_sources(self, agent_id: str | None = None) -> list[KnowledgeSource]:
        """List sources, optionally filtered by agent id."""
        with self._lock:
            sources = list(self._sources.values())
        if agent_id is not None:
            sources = [s for s in sources if s.agent_id == agent_id]
        return sources

    # ── Distillation ─────────────────────────────────────────────

    def distill(
        self,
        source_ids: list[str],
        knowledge_type: KnowledgeType,
        compression_level: CompressionLevel = CompressionLevel.MODERATE,
        title: str = "",
        tags: list[str] | None = None,
    ) -> DistilledKnowledge:
        """Distill a set of sources into a single compressed knowledge unit.

        Pipeline:
        1. Create a distillation session and mark it EXTRACTING.
        2. Fetch the requested sources.
        3. Extract key points from pooled content.
        4. Extract cross-source patterns.
        5. Generate a compressed summary.
        6. Compute sizes and fidelity.
        7. Mark the session COMPLETED and store the knowledge.

        If no valid sources are found, the session is marked FAILED and a
        failed knowledge object is returned for caller convenience.
        """
        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        knowledge_id = f"kno_{uuid.uuid4().hex[:12]}"
        tags = list(tags) if tags else []

        with self._lock:
            session = DistillationSession(
                session_id=session_id,
                agent_id="",
                source_ids=list(source_ids),
                compression_level=compression_level,
                status=DistillationStatus.EXTRACTING,
                started_at=time.time(),
            )
            self._sessions[session_id] = session

            # Fetch all requested sources that exist.
            fetched: list[KnowledgeSource] = []
            for sid in source_ids:
                src = self._sources.get(sid)
                if src is not None:
                    fetched.append(src)

            if not fetched:
                session.status = DistillationStatus.FAILED
                session.error = "No valid sources found for distillation"
                session.completed_at = time.time()
                logger.warning(
                    "Distillation %s failed: no valid sources", session_id
                )
                failed = DistilledKnowledge(
                    knowledge_id=knowledge_id,
                    source_ids=list(source_ids),
                    knowledge_type=knowledge_type,
                    title=title or "Failed Distillation",
                    summary="",
                    key_points=[],
                    patterns=[],
                    compression_level=compression_level,
                    original_size=0,
                    compressed_size=0,
                    fidelity_score=0.0,
                    tags=tags,
                    created_at=time.time(),
                    status=DistillationStatus.FAILED,
                )
                return failed

            # Use the first source's agent_id as the session owner.
            session.agent_id = fetched[0].agent_id
            session.status = DistillationStatus.COMPRESSING
            contents = [s.content for s in fetched]

        # Heavy extraction work is performed outside the lock.
        key_points = self._extract_key_points(contents, compression_level)
        patterns = self._extract_patterns(contents)
        summary = self._generate_summary(key_points, patterns)

        original_size = sum(len(c) for c in contents)
        compressed_size = len(summary) + sum(len(kp) for kp in key_points)
        fidelity = self._compute_fidelity(
            original_size, compressed_size, len(fetched)
        )

        with self._lock:
            if len(self._knowledge) >= self.MAX_KNOWLEDGE:
                oldest_kid = min(
                    self._knowledge.keys(),
                    key=lambda kid: self._knowledge[kid].created_at,
                )
                self._knowledge.pop(oldest_kid, None)
                logger.debug(
                    "Evicted oldest knowledge %s to respect MAX_KNOWLEDGE",
                    oldest_kid,
                )

            knowledge = DistilledKnowledge(
                knowledge_id=knowledge_id,
                source_ids=list(source_ids),
                knowledge_type=knowledge_type,
                title=title or f"Distilled {knowledge_type.value} knowledge",
                summary=summary,
                key_points=key_points,
                patterns=patterns,
                compression_level=compression_level,
                original_size=original_size,
                compressed_size=compressed_size,
                fidelity_score=fidelity,
                tags=tags,
                created_at=time.time(),
                status=DistillationStatus.COMPLETED,
            )
            self._knowledge[knowledge_id] = knowledge

            session.status = DistillationStatus.COMPLETED
            session.result_knowledge_id = knowledge_id
            session.completed_at = time.time()

            return knowledge

    def get_knowledge(self, knowledge_id: str) -> DistilledKnowledge | None:
        """Retrieve a single distilled knowledge unit by id."""
        with self._lock:
            return self._knowledge.get(knowledge_id)

    def list_knowledge(
        self,
        knowledge_type: KnowledgeType | None = None,
        agent_id: str | None = None,
    ) -> list[DistilledKnowledge]:
        """List distilled knowledge, optionally filtered by type or agent.

        Agent filtering relies on the knowledge's source_ids mapping back
        to sources owned by the given agent. A knowledge unit belongs to an
        agent if any of its sources was registered by that agent.
        """
        with self._lock:
            items = list(self._knowledge.values())
            if knowledge_type is not None:
                items = [
                    k for k in items if k.knowledge_type == knowledge_type
                ]
            if agent_id is not None:
                allowed = {
                    sid
                    for sid, src in self._sources.items()
                    if src.agent_id == agent_id
                }
                items = [
                    k
                    for k in items
                    if any(sid in allowed for sid in k.source_ids)
                ]
        return items

    # ── Transfer ─────────────────────────────────────────────────

    def transfer_knowledge(
        self,
        knowledge_id: str,
        source_agent_id: str,
        target_agent_id: str,
    ) -> KnowledgeTransfer:
        """Initiate a knowledge transfer between two agents.

        If the knowledge unit does not exist, the transfer is recorded with
        status FAILED and an explanatory note. Otherwise it is recorded as
        COMPLETED (in-memory transfers are immediate).
        """
        with self._lock:
            knowledge = self._knowledge.get(knowledge_id)
            if knowledge is None:
                transfer = KnowledgeTransfer(
                    transfer_id=f"xfr_{uuid.uuid4().hex[:12]}",
                    source_agent_id=source_agent_id,
                    target_agent_id=target_agent_id,
                    knowledge_id=knowledge_id,
                    status=TransferStatus.FAILED,
                    transferred_at=None,
                    notes=f"Knowledge {knowledge_id} not found",
                )
            else:
                transfer = KnowledgeTransfer(
                    transfer_id=f"xfr_{uuid.uuid4().hex[:12]}",
                    source_agent_id=source_agent_id,
                    target_agent_id=target_agent_id,
                    knowledge_id=knowledge_id,
                    status=TransferStatus.COMPLETED,
                    transferred_at=time.time(),
                    notes="",
                )
            self._transfers[transfer.transfer_id] = transfer
            return transfer

    def get_transfer(self, transfer_id: str) -> KnowledgeTransfer | None:
        """Retrieve a transfer record by id."""
        with self._lock:
            return self._transfers.get(transfer_id)

    def list_transfers(
        self,
        source_agent_id: str | None = None,
        target_agent_id: str | None = None,
    ) -> list[KnowledgeTransfer]:
        """List transfers, optionally filtered by source or target agent."""
        with self._lock:
            items = list(self._transfers.values())
        if source_agent_id is not None:
            items = [t for t in items if t.source_agent_id == source_agent_id]
        if target_agent_id is not None:
            items = [t for t in items if t.target_agent_id == target_agent_id]
        return items

    def acknowledge_transfer(self, transfer_id: str) -> KnowledgeTransfer | None:
        """Mark a transfer as acknowledged by the target agent.

        Returns the updated transfer, or None if the transfer id is unknown.
        A transfer that was IN_PROGRESS is promoted to COMPLETED on
        acknowledgment.
        """
        with self._lock:
            transfer = self._transfers.get(transfer_id)
            if transfer is None:
                return None
            transfer.acknowledged = True
            if transfer.status == TransferStatus.IN_PROGRESS:
                transfer.status = TransferStatus.COMPLETED
            return transfer

    # ── Query ────────────────────────────────────────────────────

    def query_knowledge(
        self,
        agent_id: str,
        query_text: str,
        top_k: int = 5,
    ) -> KnowledgeQuery:
        """Query distilled knowledge by keyword matching.

        Splits the query into words and scores each knowledge unit by
        counting matching words across title, summary, and key points.
        Returns the top_k highest-scoring matches (only those with a
        positive score). The query is recorded for observability.
        """
        query_id = f"qry_{uuid.uuid4().hex[:12]}"
        query_words = [w.lower() for w in query_text.split() if w.strip()]

        with self._lock:
            candidates = list(self._knowledge.values())

        scored: list[tuple[float, DistilledKnowledge]] = []
        for k in candidates:
            score = self._score_match(query_words, k)
            if score > 0.0:
                scored.append((score, k))

        scored.sort(key=lambda item: item[0], reverse=True)
        if top_k > 0:
            scored = scored[:top_k]

        matched_ids = [k.knowledge_id for _, k in scored]
        top_score = scored[0][0] if scored else 0.0

        query = KnowledgeQuery(
            query_id=query_id,
            agent_id=agent_id,
            query_text=query_text,
            matched_knowledge_ids=matched_ids,
            top_score=top_score,
            created_at=time.time(),
        )

        with self._lock:
            if len(self._queries) >= self.MAX_QUERIES:
                # Drop the oldest query to make room for the new one.
                self._queries.pop(0)
            self._queries.append(query)

        return query

    # ── Stats ────────────────────────────────────────────────────

    def get_stats(self) -> DistillerStats:
        """Compute aggregate statistics about distiller activity."""
        with self._lock:
            total_sources = len(self._sources)
            total_distilled = len(self._knowledge)
            total_sessions = len(self._sessions)
            total_transfers = len(self._transfers)
            total_queries = len(self._queries)

            by_type: dict[str, int] = {}
            fidelity_sum = 0.0
            ratio_sum = 0.0
            for k in self._knowledge.values():
                kt = k.knowledge_type.value
                by_type[kt] = by_type.get(kt, 0) + 1
                fidelity_sum += k.fidelity_score
                ratio_sum += k.compression_ratio

            if total_distilled > 0:
                avg_fidelity = fidelity_sum / total_distilled
                avg_ratio = ratio_sum / total_distilled
            else:
                avg_fidelity = 0.0
                avg_ratio = 0.0

            return DistillerStats(
                total_sources=total_sources,
                total_distilled=total_distilled,
                total_sessions=total_sessions,
                total_transfers=total_transfers,
                total_queries=total_queries,
                avg_compression_ratio=avg_ratio,
                avg_fidelity=avg_fidelity,
                distilled_by_type=dict(by_type),
            )

    # ── Internal Helpers ─────────────────────────────────────────

    def _extract_key_points(
        self,
        contents: list[str],
        compression_level: CompressionLevel,
    ) -> list[str]:
        """Extract the top-N most informative sentences across all contents.

        Each content is split into sentences on ". ". All sentences are pooled
        and scored by a combination of length (longer is more informative up
        to a cap) and keyword richness. The top N sentences are returned,
        where N depends on the compression level.
        """
        if not contents:
            return []

        target_count = _KEY_POINTS_BY_LEVEL.get(compression_level, 5)
        if target_count <= 0:
            return []

        # Pool all sentences from all contents.
        sentences: list[str] = []
        for content in contents:
            if not content:
                continue
            for raw in content.split(". "):
                sentence = raw.strip()
                if sentence:
                    sentences.append(sentence)

        if not sentences:
            return []

        # Compute keyword frequency across the pooled sentence corpus.
        word_freq: dict[str, int] = {}
        for sentence in sentences:
            for word in sentence.lower().split():
                cleaned = word.strip(".,;:!?\"'()[]{}")
                if cleaned and cleaned not in _STOPWORDS:
                    word_freq[cleaned] = word_freq.get(cleaned, 0) + 1

        # Score each sentence: blend of length signal and keyword richness.
        scored_sentences: list[tuple[float, int, str]] = []
        for idx, sentence in enumerate(sentences):
            words = [
                w.strip(".,;:!?\"'()[]{}")
                for w in sentence.lower().split()
            ]
            words = [w for w in words if w and w not in _STOPWORDS]
            if not words:
                keyword_score = 0.0
            else:
                keyword_score = sum(word_freq.get(w, 0) for w in words) / len(words)

            # Length signal: informative up to ~120 chars, then tapers off.
            length_signal = min(len(sentence), 120) / 120.0

            # Stability tiebreaker: prefer earlier sentences on ties.
            score = keyword_score * 0.7 + length_signal * 0.3
            scored_sentences.append((score, -idx, sentence))

        scored_sentences.sort(reverse=True)
        top = scored_sentences[:target_count]

        # Re-order selected sentences by their original pooled order to
        # preserve narrative flow in the resulting key points list.
        top_with_idx = sorted(top, key=lambda item: -item[1])
        return [s for _, _, s in top_with_idx]

    def _extract_patterns(self, contents: list[str]) -> list[str]:
        """Find words appearing in more than 50% of contents.

        Tokenizes each content independently, then promotes tokens whose
        document frequency exceeds half the number of contents. Returns the
        resulting terms as pattern strings, ordered by frequency descending.
        """
        if not contents:
            return []

        threshold = len(contents) / 2.0
        doc_freq: dict[str, int] = {}
        total_freq: dict[str, int] = {}

        for content in contents:
            if not content:
                continue
            seen_in_doc: set[str] = set()
            for word in content.lower().split():
                cleaned = word.strip(".,;:!?\"'()[]{}")
                if not cleaned or cleaned in _STOPWORDS:
                    continue
                if len(cleaned) < 3:
                    continue
                seen_in_doc.add(cleaned)
            for token in seen_in_doc:
                doc_freq[token] = doc_freq.get(token, 0) + 1
                total_freq[token] = total_freq.get(token, 0) + 1

        patterns: list[tuple[int, str]] = []
        for token, freq in doc_freq.items():
            if freq > threshold:
                patterns.append((total_freq[token], token))

        patterns.sort(reverse=True)
        return [token for _, token in patterns]

    def _generate_summary(self, key_points: list[str], patterns: list[str]) -> str:
        """Build a compressed summary from key points and patterns.

        Joins key points into a single paragraph and, when patterns are
        present, appends a "Common patterns:" trailer listing them.
        """
        if not key_points:
            body = ""
        else:
            body = ". ".join(key_points)
            if not body.endswith("."):
                body += "."

        if patterns:
            trailer = "Common patterns: " + ", ".join(patterns)
            if body:
                return body + " " + trailer
            return trailer
        return body

    def _compute_fidelity(
        self,
        original_size: int,
        compressed_size: int,
        num_sources: int,
    ) -> float:
        """Estimate fidelity of the compressed knowledge.

        Fidelity blends the compression ratio (compressed / original) with a
        bonus proportional to the number of sources distilled. The result is
        clamped to [0, 1].

        Formula:
            ratio = compressed_size / max(original_size, 1)
            fidelity = min(1.0, 0.3 + ratio * 0.7 + num_sources * 0.02)
        """
        if original_size <= 0:
            return 0.0
        ratio = compressed_size / max(original_size, 1)
        fidelity = 0.3 + ratio * 0.7 + num_sources * 0.02
        # Clamp to [0, 1]; negative inputs should never happen but guard anyway.
        return max(0.0, min(1.0, fidelity))

    def _score_match(
        self,
        query_words: list[str],
        knowledge: DistilledKnowledge,
    ) -> float:
        """Score a knowledge unit against a list of query words.

        Counts how many query words appear (case-insensitively) in the
        concatenated title + summary + key_points, then normalizes by the
        number of query words. Returns 0.0 when the query is empty.
        """
        if not query_words:
            return 0.0

        haystack_parts: list[str] = [knowledge.title, knowledge.summary]
        haystack_parts.extend(knowledge.key_points)
        haystack = " ".join(haystack_parts).lower()
        haystack_tokens = haystack.split()

        # Use a set for O(1) membership tests on query words.
        query_set = set(query_words)
        haystack_token_set = set(haystack_tokens)

        matched = sum(1 for w in query_set if w in haystack_token_set)
        return matched / len(query_set)


# ── Module-level Singleton ────────────────────────────────────────

_global_distiller: AgentKnowledgeDistiller | None = None
_global_distiller_lock = threading.Lock()


def get_knowledge_distiller() -> AgentKnowledgeDistiller:
    """Return the process-wide singleton distiller instance."""
    global _global_distiller
    with _global_distiller_lock:
        if _global_distiller is None:
            _global_distiller = AgentKnowledgeDistiller()
        return _global_distiller


def reset_knowledge_distiller() -> None:
    """Reset the singleton distiller (primarily for tests)."""
    global _global_distiller
    with _global_distiller_lock:
        _global_distiller = None
