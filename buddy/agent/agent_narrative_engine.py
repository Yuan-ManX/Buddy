"""Agent Narrative Engine - coherent storytelling from discrete events.

Constructs coherent narratives from events and experiences, enabling storytelling,
experience sharing, and sense-making. Discrete events are transformed into
structured stories that carry a plot, characters, themes, and arcs.

Each narrative groups a sequence of events together with the characters that
participate in them, the themes they illustrate, and the threads that trace
sub-plots across the narrative. Narratives move through a lifecycle from draft
to structured, refined, published, and finally archived. Threads model the
classic plot arc (setup, rising action, climax, falling action, resolution)
and carry a tension level that reflects how much conflict they hold.

All public state mutations are guarded by a threading.Lock to ensure thread
safety when the engine is shared across agent threads. The engine is intended
to be self-contained with no external dependencies beyond the Python standard
library.
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ═══════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════

class NarrativeType(Enum):
    """Kinds of narratives the engine can construct."""
    PERSONAL = "personal"
    PROCEDURAL = "procedural"
    EXPLANATORY = "explanatory"
    PERSUASIVE = "persuasive"
    DESCRIPTIVE = "descriptive"
    REFLECTIVE = "reflective"


class NarrativeStatus(Enum):
    """Lifecycle states of a narrative."""
    DRAFT = "draft"
    STRUCTURED = "structured"
    REFINED = "refined"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class PlotArc(Enum):
    """Stages of a classical narrative plot arc."""
    SETUP = "setup"
    RISING_ACTION = "rising_action"
    CLIMAX = "climax"
    FALLING_ACTION = "falling_action"
    RESOLUTION = "resolution"


class NarrativeTense(Enum):
    """Temporal framing the narrative is told in."""
    PAST = "past"
    PRESENT = "present"
    FUTURE = "future"
    CONDITIONAL = "conditional"


class PerspectiveType(Enum):
    """Point of view from which the narrative is told."""
    FIRST_PERSON = "first_person"
    SECOND_PERSON = "second_person"
    THIRD_PERSON = "third_person"
    OMNISCIENT = "omniscient"


# ═══════════════════════════════════════════════════════════
# Dataclasses
# ═══════════════════════════════════════════════════════════

@dataclass
class NarrativeEvent:
    """A single discrete event that contributes to a narrative.

    Events are the atomic units of a story. Each event records what happened,
    who participated, where it took place, how significant it is, the emotional
    tone it carries, and which prior events causally led to it. The
    `causal_predecessors` list stores event ids that this event depends on,
    allowing the engine to reconstruct chains of cause and effect.
    """
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    narrative_id: str = ""
    timestamp: float = field(default_factory=time.time)
    description: str = ""
    participants: list[str] = field(default_factory=list)
    location: str = ""
    significance: float = 0.5
    emotional_tone: str = ""
    causal_predecessors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "narrative_id": self.narrative_id,
            "timestamp": self.timestamp,
            "description": self.description,
            "participants": list(self.participants),
            "location": self.location,
            "significance": self.significance,
            "emotional_tone": self.emotional_tone,
            "causal_predecessors": list(self.causal_predecessors),
        }


@dataclass
class NarrativeCharacter:
    """A character that appears within a narrative.

    Characters carry a role (e.g. protagonist, mentor, antagonist), a free-form
    description, a list of motivations, a mapping of relationships to other
    characters, and an arc summary describing how they change over the course
    of the story.
    """
    character_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    role: str = ""
    description: str = ""
    motivations: list[str] = field(default_factory=list)
    relationships: dict[str, str] = field(default_factory=dict)
    arc_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "character_id": self.character_id,
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "motivations": list(self.motivations),
            "relationships": dict(self.relationships),
            "arc_summary": self.arc_summary,
        }


@dataclass
class NarrativeTheme:
    """A recurring theme illustrated by one or more events.

    The `relevance_score` (in [0, 1]) expresses how central the theme is to the
    narrative, and `occurrences` lists the event ids that exemplify the theme.
    """
    theme_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    relevance_score: float = 0.5
    occurrences: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "theme_id": self.theme_id,
            "name": self.name,
            "description": self.description,
            "relevance_score": self.relevance_score,
            "occurrences": list(self.occurrences),
        }


@dataclass
class NarrativeThread:
    """A sub-plot thread that traces a sequence of events through an arc.

    Threads group related events and track their position along the plot arc.
    The `tension_level` (in [0, 1]) reflects how much unresolved conflict the
    thread currently holds; it drops to zero once the thread is resolved.
    """
    thread_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    narrative_id: str = ""
    name: str = ""
    description: str = ""
    events: list[str] = field(default_factory=list)
    arc_type: PlotArc = PlotArc.SETUP
    tension_level: float = 0.0
    resolved: bool = False
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "thread_id": self.thread_id,
            "narrative_id": self.narrative_id,
            "name": self.name,
            "description": self.description,
            "events": list(self.events),
            "arc_type": self.arc_type.value,
            "tension_level": self.tension_level,
            "resolved": self.resolved,
            "created_at": self.created_at,
        }


@dataclass
class Narrative:
    """A structured story assembled from events, characters, themes, and threads.

    A narrative is the top-level container produced by the engine. It carries
    framing metadata (type, status, perspective, tense), the ordered list of
    events that compose it, the characters and themes it involves, and the
    threads that trace its sub-plots. A generated `summary` captures the story
    in prose; `published_at` records when the narrative was first published.
    """
    narrative_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    agent_id: str = ""
    title: str = ""
    narrative_type: NarrativeType = NarrativeType.PERSONAL
    status: NarrativeStatus = NarrativeStatus.DRAFT
    perspective: PerspectiveType = PerspectiveType.FIRST_PERSON
    tense: NarrativeTense = NarrativeTense.PAST
    events: list[NarrativeEvent] = field(default_factory=list)
    characters: list[NarrativeCharacter] = field(default_factory=list)
    themes: list[NarrativeTheme] = field(default_factory=list)
    threads: list[NarrativeThread] = field(default_factory=list)
    summary: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    published_at: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "narrative_id": self.narrative_id,
            "agent_id": self.agent_id,
            "title": self.title,
            "narrative_type": self.narrative_type.value,
            "status": self.status.value,
            "perspective": self.perspective.value,
            "tense": self.tense.value,
            "events": [e.to_dict() for e in self.events],
            "characters": [c.to_dict() for c in self.characters],
            "themes": [t.to_dict() for t in self.themes],
            "threads": [th.to_dict() for th in self.threads],
            "summary": self.summary,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "published_at": self.published_at,
        }


@dataclass
class NarrativeStats:
    """Aggregate usage statistics for the entire narrative engine."""
    total_narratives: int = 0
    total_events: int = 0
    total_characters: int = 0
    total_themes: int = 0
    narratives_by_type: dict[str, int] = field(default_factory=dict)
    narratives_by_status: dict[str, int] = field(default_factory=dict)
    avg_events_per_narrative: float = 0.0
    avg_themes_per_narrative: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_narratives": self.total_narratives,
            "total_events": self.total_events,
            "total_characters": self.total_characters,
            "total_themes": self.total_themes,
            "narratives_by_type": dict(self.narratives_by_type),
            "narratives_by_status": dict(self.narratives_by_status),
            "avg_events_per_narrative": self.avg_events_per_narrative,
            "avg_themes_per_narrative": self.avg_themes_per_narrative,
        }


# ═══════════════════════════════════════════════════════════
# Main Engine Class
# ═══════════════════════════════════════════════════════════

class AgentNarrativeEngine:
    """Narrative construction engine for coherent storytelling from events.

    Transforms discrete events into structured stories with plots, characters,
    themes, and arcs. A narrative groups an ordered sequence of events together
    with the characters that participate in them, the themes they illustrate,
    and the threads that trace sub-plots across the narrative. Narratives move
    through a lifecycle (draft -> structured -> refined -> published -> archived)
    and threads track their position along a classical plot arc with an
    associated tension level.

    The engine maintains a global index of events and threads so they can be
    retrieved directly by id, in addition to their membership within a
    narrative. Summary generation composes a prose recap from the narrative's
    events, participants, locations, themes, and emotional arc.

    All public state mutations are guarded by a threading.Lock to ensure thread
    safety when the engine is shared across agent threads.
    """

    # Capacity caps to keep memory bounded under sustained use.
    MAX_NARRATIVES: int = 1000
    MAX_EVENTS_PER_NARRATIVE: int = 1000
    MAX_CHARACTERS_PER_NARRATIVE: int = 200
    MAX_THEMES_PER_NARRATIVE: int = 100
    MAX_THREADS_PER_NARRATIVE: int = 100

    # Base tension contributed by each plot arc stage. Climax carries the most
    # tension; resolution carries the least.
    _ARC_TENSION: dict[PlotArc, float] = {
        PlotArc.SETUP: 0.2,
        PlotArc.RISING_ACTION: 0.5,
        PlotArc.CLIMAX: 0.9,
        PlotArc.FALLING_ACTION: 0.6,
        PlotArc.RESOLUTION: 0.1,
    }

    def __init__(self) -> None:
        self._narratives: dict[str, Narrative] = {}
        # Global indices for direct id lookups of events and threads.
        self._events: dict[str, NarrativeEvent] = {}
        self._threads: dict[str, NarrativeThread] = {}
        self._lock = threading.Lock()

    # ── Narrative management ───────────────────────────────

    def create_narrative(
        self,
        agent_id: str,
        title: str,
        narrative_type: NarrativeType = NarrativeType.PERSONAL,
        perspective: PerspectiveType = PerspectiveType.FIRST_PERSON,
        tense: NarrativeTense = NarrativeTense.PAST,
    ) -> Narrative:
        """Create and register a new narrative.

        Args:
            agent_id: The agent that owns this narrative.
            title: A short human-readable title for the story.
            narrative_type: The kind of narrative to construct.
            perspective: The point of view the story is told from.
            tense: The temporal framing of the story.

        Returns:
            The newly created Narrative in the DRAFT status.
        """
        with self._lock:
            # Evict the oldest narrative if we are at capacity.
            if len(self._narratives) >= self.MAX_NARRATIVES:
                oldest_id = min(
                    self._narratives.keys(),
                    key=lambda nid: self._narratives[nid].created_at,
                )
                self._evict_narrative(oldest_id)

            narrative = Narrative(
                agent_id=agent_id,
                title=title,
                narrative_type=narrative_type,
                perspective=perspective,
                tense=tense,
            )
            self._narratives[narrative.narrative_id] = narrative
            return narrative

    def get_narrative(self, narrative_id: str) -> Narrative | None:
        """Retrieve a narrative by id, or None if not found."""
        with self._lock:
            return self._narratives.get(narrative_id)

    def list_narratives(
        self,
        agent_id: str | None = None,
        status: NarrativeStatus | None = None,
        narrative_type: NarrativeType | None = None,
    ) -> list[Narrative]:
        """List narratives, optionally filtered by owner, status, and type.

        Args:
            agent_id: If provided, only return narratives owned by this agent.
            status: If provided, only return narratives in this status.
            narrative_type: If provided, only return narratives of this type.

        Returns:
            A fresh list of matching narratives ordered by creation time.
        """
        with self._lock:
            result: list[Narrative] = []
            for narrative in self._narratives.values():
                if agent_id is not None and narrative.agent_id != agent_id:
                    continue
                if status is not None and narrative.status != status:
                    continue
                if narrative_type is not None and narrative.narrative_type != narrative_type:
                    continue
                result.append(narrative)
            result.sort(key=lambda n: n.created_at)
            return result

    def update_narrative(
        self,
        narrative_id: str,
        title: str | None = None,
        summary: str | None = None,
        status: NarrativeStatus | None = None,
    ) -> Narrative:
        """Update mutable fields of a narrative.

        Any argument that is None is left unchanged. Transitioning the status
        to PUBLISHED records the publication timestamp the first time it
        occurs.

        Args:
            narrative_id: The narrative to update.
            title: New title, or None to keep the current title.
            summary: New summary, or None to keep the current summary.
            status: New status, or None to keep the current status.

        Returns:
            The updated Narrative.

        Raises:
            KeyError: If the narrative does not exist.
        """
        with self._lock:
            narrative = self._narratives.get(narrative_id)
            if narrative is None:
                raise KeyError(f"Narrative not found: {narrative_id}")

            if title is not None:
                narrative.title = title
            if summary is not None:
                narrative.summary = summary
            if status is not None:
                narrative.status = status
                if status == NarrativeStatus.PUBLISHED and narrative.published_at is None:
                    narrative.published_at = time.time()
            narrative.updated_at = time.time()
            return narrative

    def delete_narrative(self, narrative_id: str) -> bool:
        """Delete a narrative and any associated events and threads.

        Returns True if the narrative existed and was deleted, False otherwise.
        """
        with self._lock:
            if narrative_id not in self._narratives:
                return False
            self._evict_narrative(narrative_id)
            return True

    # ── Event management ───────────────────────────────────

    def add_event(
        self,
        narrative_id: str,
        description: str,
        participants: list[str] | None = None,
        location: str = "",
        significance: float = 0.5,
        emotional_tone: str = "",
        causal_predecessors: list[str] | None = None,
    ) -> NarrativeEvent:
        """Append a new event to a narrative.

        The event is added to the end of the narrative's event list and indexed
        globally so it can be retrieved by id. Significance is clamped to the
        range [0, 1].

        Args:
            narrative_id: The narrative the event belongs to.
            description: What happened in the event.
            participants: Names of the characters or agents involved.
            location: Where the event took place.
            significance: How important the event is, in [0, 1].
            emotional_tone: A label for the emotional flavour of the event.
            causal_predecessors: Event ids that causally led to this event.

        Returns:
            The newly created NarrativeEvent.

        Raises:
            KeyError: If the narrative does not exist.
            ValueError: If the per-narrative event cap has been reached.
        """
        with self._lock:
            narrative = self._narratives.get(narrative_id)
            if narrative is None:
                raise KeyError(f"Narrative not found: {narrative_id}")
            if len(narrative.events) >= self.MAX_EVENTS_PER_NARRATIVE:
                raise ValueError("Maximum events per narrative reached")

            event = NarrativeEvent(
                narrative_id=narrative_id,
                description=description,
                participants=list(participants) if participants else [],
                location=location,
                significance=max(0.0, min(1.0, significance)),
                emotional_tone=emotional_tone,
                causal_predecessors=list(causal_predecessors) if causal_predecessors else [],
            )
            narrative.events.append(event)
            self._events[event.event_id] = event
            narrative.updated_at = time.time()
            return event

    def get_event(self, event_id: str) -> NarrativeEvent | None:
        """Retrieve an event by id from the global index, or None if not found."""
        with self._lock:
            return self._events.get(event_id)

    def list_events(self, narrative_id: str) -> list[NarrativeEvent]:
        """List all events in a narrative in insertion order.

        Returns an empty list if the narrative does not exist.
        """
        with self._lock:
            narrative = self._narratives.get(narrative_id)
            if narrative is None:
                return []
            return list(narrative.events)

    # ── Character management ───────────────────────────────

    def add_character(
        self,
        narrative_id: str,
        name: str,
        role: str = "",
        description: str = "",
        motivations: list[str] | None = None,
    ) -> NarrativeCharacter:
        """Add a character to a narrative.

        Args:
            narrative_id: The narrative the character belongs to.
            name: The character's display name.
            role: The character's role (e.g. protagonist, mentor).
            description: A free-form description of the character.
            motivations: What drives the character.

        Returns:
            The newly created NarrativeCharacter.

        Raises:
            KeyError: If the narrative does not exist.
            ValueError: If the per-narrative character cap has been reached.
        """
        with self._lock:
            narrative = self._narratives.get(narrative_id)
            if narrative is None:
                raise KeyError(f"Narrative not found: {narrative_id}")
            if len(narrative.characters) >= self.MAX_CHARACTERS_PER_NARRATIVE:
                raise ValueError("Maximum characters per narrative reached")

            character = NarrativeCharacter(
                name=name,
                role=role,
                description=description,
                motivations=list(motivations) if motivations else [],
            )
            narrative.characters.append(character)
            narrative.updated_at = time.time()
            return character

    def list_characters(self, narrative_id: str) -> list[NarrativeCharacter]:
        """List all characters in a narrative.

        Returns an empty list if the narrative does not exist.
        """
        with self._lock:
            narrative = self._narratives.get(narrative_id)
            if narrative is None:
                return []
            return list(narrative.characters)

    # ── Theme management ───────────────────────────────────

    def add_theme(
        self,
        narrative_id: str,
        name: str,
        description: str = "",
        relevance_score: float = 0.5,
    ) -> NarrativeTheme:
        """Add a theme to a narrative.

        Args:
            narrative_id: The narrative the theme belongs to.
            name: The theme's name.
            description: A description of how the theme manifests.
            relevance_score: How central the theme is, in [0, 1].

        Returns:
            The newly created NarrativeTheme.

        Raises:
            KeyError: If the narrative does not exist.
            ValueError: If the per-narrative theme cap has been reached.
        """
        with self._lock:
            narrative = self._narratives.get(narrative_id)
            if narrative is None:
                raise KeyError(f"Narrative not found: {narrative_id}")
            if len(narrative.themes) >= self.MAX_THEMES_PER_NARRATIVE:
                raise ValueError("Maximum themes per narrative reached")

            theme = NarrativeTheme(
                name=name,
                description=description,
                relevance_score=max(0.0, min(1.0, relevance_score)),
            )
            narrative.themes.append(theme)
            narrative.updated_at = time.time()
            return theme

    def list_themes(self, narrative_id: str) -> list[NarrativeTheme]:
        """List all themes in a narrative.

        Returns an empty list if the narrative does not exist.
        """
        with self._lock:
            narrative = self._narratives.get(narrative_id)
            if narrative is None:
                return []
            return list(narrative.themes)

    # ── Thread management ──────────────────────────────────

    def create_thread(
        self,
        narrative_id: str,
        name: str,
        description: str = "",
        event_ids: list[str] | None = None,
        arc_type: PlotArc = PlotArc.SETUP,
    ) -> NarrativeThread:
        """Create a sub-plot thread that links a set of events.

        The referenced event ids must all belong to the given narrative. The
        thread's initial tension level is derived from its arc stage and the
        number of linked events.

        Args:
            narrative_id: The narrative the thread belongs to.
            name: The thread's name.
            description: A description of the sub-plot.
            event_ids: Event ids to link into this thread.
            arc_type: The thread's position along the plot arc.

        Returns:
            The newly created NarrativeThread.

        Raises:
            KeyError: If the narrative does not exist.
            ValueError: If the per-narrative thread cap is reached, or a
                referenced event does not belong to the narrative.
        """
        with self._lock:
            narrative = self._narratives.get(narrative_id)
            if narrative is None:
                raise KeyError(f"Narrative not found: {narrative_id}")
            if len(narrative.threads) >= self.MAX_THREADS_PER_NARRATIVE:
                raise ValueError("Maximum threads per narrative reached")

            linked_ids = list(event_ids) if event_ids else []
            for eid in linked_ids:
                event = self._events.get(eid)
                if event is None or event.narrative_id != narrative_id:
                    raise ValueError(
                        f"Event not part of narrative: {eid}"
                    )

            thread = NarrativeThread(
                narrative_id=narrative_id,
                name=name,
                description=description,
                events=linked_ids,
                arc_type=arc_type,
            )
            thread.tension_level = self._compute_tension(arc_type, linked_ids)
            narrative.threads.append(thread)
            self._threads[thread.thread_id] = thread
            narrative.updated_at = time.time()
            return thread

    def list_threads(self, narrative_id: str) -> list[NarrativeThread]:
        """List all threads in a narrative.

        Returns an empty list if the narrative does not exist.
        """
        with self._lock:
            narrative = self._narratives.get(narrative_id)
            if narrative is None:
                return []
            return list(narrative.threads)

    def resolve_thread(self, thread_id: str, resolution: str) -> NarrativeThread:
        """Mark a thread as resolved and record its resolution text.

        Resolving a thread sets its arc to RESOLUTION, drops its tension to
        zero, and appends the resolution text to the thread's description so
        the outcome is preserved alongside the original sub-plot description.

        Args:
            thread_id: The thread to resolve.
            resolution: A short description of how the sub-plot concluded.

        Returns:
            The resolved NarrativeThread.

        Raises:
            KeyError: If the thread does not exist.
        """
        with self._lock:
            thread = self._threads.get(thread_id)
            if thread is None:
                raise KeyError(f"Thread not found: {thread_id}")

            thread.resolved = True
            thread.tension_level = 0.0
            thread.arc_type = PlotArc.RESOLUTION
            if resolution:
                suffix = f"[Resolution: {resolution}]"
                thread.description = (
                    f"{thread.description} {suffix}".strip()
                    if thread.description
                    else suffix
                )

            narrative = self._narratives.get(thread.narrative_id)
            if narrative is not None:
                narrative.updated_at = time.time()
            return thread

    # ── Summary generation and stats ───────────────────────

    def generate_summary(self, narrative_id: str) -> str:
        """Auto-generate a prose summary for a narrative from its events.

        Composes a recap that captures the narrative's framing, the span of
        events, the locations and participants involved, the themes, the
        opening, middle, and closing beats, the emotional arc, and the thread
        resolution status. The generated summary is stored on the narrative
        and returned.

        Args:
            narrative_id: The narrative to summarise.

        Returns:
            The generated summary string.

        Raises:
            KeyError: If the narrative does not exist.
        """
        with self._lock:
            narrative = self._narratives.get(narrative_id)
            if narrative is None:
                raise KeyError(f"Narrative not found: {narrative_id}")

            summary = self._compose_summary(narrative)
            narrative.summary = summary
            narrative.updated_at = time.time()
            return summary

    def get_stats(self) -> NarrativeStats:
        """Return aggregate statistics about engine usage.

        Computes totals across all narratives (narratives, events, characters,
        themes), the distribution of narratives by type and status, and the
        average number of events and themes per narrative.
        """
        with self._lock:
            total_narratives = len(self._narratives)
            by_type: dict[str, int] = {}
            by_status: dict[str, int] = {}
            total_events = 0
            total_characters = 0
            total_themes = 0

            for narrative in self._narratives.values():
                type_key = narrative.narrative_type.value
                status_key = narrative.status.value
                by_type[type_key] = by_type.get(type_key, 0) + 1
                by_status[status_key] = by_status.get(status_key, 0) + 1
                total_events += len(narrative.events)
                total_characters += len(narrative.characters)
                total_themes += len(narrative.themes)

            if total_narratives > 0:
                avg_events = total_events / total_narratives
                avg_themes = total_themes / total_narratives
            else:
                avg_events = 0.0
                avg_themes = 0.0

            return NarrativeStats(
                total_narratives=total_narratives,
                total_events=total_events,
                total_characters=total_characters,
                total_themes=total_themes,
                narratives_by_type=by_type,
                narratives_by_status=by_status,
                avg_events_per_narrative=round(avg_events, 3),
                avg_themes_per_narrative=round(avg_themes, 3),
            )

    # ── Private helpers ────────────────────────────────────
    # These helpers assume the caller already holds self._lock.

    def _evict_narrative(self, narrative_id: str) -> None:
        """Remove a narrative and its events/threads from all indices.

        Must be called while holding self._lock. Silently does nothing if the
        narrative id is unknown.
        """
        narrative = self._narratives.pop(narrative_id, None)
        if narrative is None:
            return
        for event in narrative.events:
            self._events.pop(event.event_id, None)
        for thread in narrative.threads:
            self._threads.pop(thread.thread_id, None)

    def _compute_tension(
        self,
        arc_type: PlotArc,
        event_ids: list[str],
    ) -> float:
        """Compute an initial tension level for a thread.

        Combines the base tension of the arc stage with a small bonus per
        linked event, then squashes the result through tanh so it stays in
        the open interval (0, 1).
        """
        base = self._ARC_TENSION.get(arc_type, 0.3)
        bonus = min(0.3, len(event_ids) * 0.03)
        return round(math.tanh(base + bonus), 3)

    def _compose_summary(self, narrative: Narrative) -> str:
        """Build a human-readable summary from a narrative's contents.

        Must be called while holding self._lock.
        """
        parts: list[str] = []

        title = narrative.title or "Untitled narrative"
        parts.append(f"[{narrative.narrative_type.value}] {title}")

        perspective_label = narrative.perspective.value.replace("_", " ")
        parts.append(
            f"Told from the {perspective_label} perspective "
            f"in the {narrative.tense.value} tense."
        )

        events = list(narrative.events)
        if not events:
            parts.append("No events have been recorded yet.")
            return " ".join(parts)

        events_sorted = sorted(events, key=lambda e: e.timestamp)
        parts.append(f"Spans {len(events_sorted)} event(s).")

        # Locations mentioned across events, preserving first-seen order.
        locations: list[str] = []
        seen_locations: set[str] = set()
        for event in events_sorted:
            if event.location and event.location not in seen_locations:
                seen_locations.add(event.location)
                locations.append(event.location)
        if locations:
            parts.append("Unfolds across: " + ", ".join(locations) + ".")

        # Participants aggregated across events, preserving first-seen order.
        participants: list[str] = []
        seen_participants: set[str] = set()
        for event in events_sorted:
            for participant in event.participants:
                if participant and participant not in seen_participants:
                    seen_participants.add(participant)
                    participants.append(participant)
        if participants:
            parts.append("Key participants: " + ", ".join(participants[:8]) + ".")

        # Themes, ordered by relevance (highest first).
        if narrative.themes:
            theme_names = [
                t.name for t in sorted(
                    narrative.themes,
                    key=lambda x: x.relevance_score,
                    reverse=True,
                )
                if t.name
            ]
            if theme_names:
                parts.append("Themes: " + ", ".join(theme_names[:6]) + ".")

        # Plot beats: opening, middle, closing.
        parts.append(f"It opens with: {events_sorted[0].description}.")
        if len(events_sorted) > 2:
            middle = events_sorted[len(events_sorted) // 2]
            parts.append(f"It builds through: {middle.description}.")
        if len(events_sorted) > 1:
            closing = events_sorted[-1]
            parts.append(f"It closes with: {closing.description}.")

        # Emotional arc, drawn from the first and last tones present.
        tones = [e.emotional_tone for e in events_sorted if e.emotional_tone]
        if tones:
            parts.append(
                f"Emotional tone shifts from '{tones[0]}' to '{tones[-1]}'."
            )

        # Average significance, computed with math.fsum for stability.
        total_significance = math.fsum(e.significance for e in events_sorted)
        avg_significance = total_significance / len(events_sorted)
        parts.append(f"Average event significance: {round(avg_significance, 2)}.")

        # Thread resolution status.
        if narrative.threads:
            resolved_count = sum(1 for t in narrative.threads if t.resolved)
            parts.append(
                f"Contains {len(narrative.threads)} thread(s), "
                f"{resolved_count} resolved."
            )

        return " ".join(parts)


# ═══════════════════════════════════════════════════════════
# Module-level Singleton
# ═══════════════════════════════════════════════════════════

_narrative_engine: AgentNarrativeEngine | None = None
_narrative_engine_lock = threading.Lock()


def get_narrative_engine() -> AgentNarrativeEngine:
    """Return the process-wide singleton AgentNarrativeEngine instance."""
    global _narrative_engine
    with _narrative_engine_lock:
        if _narrative_engine is None:
            _narrative_engine = AgentNarrativeEngine()
        return _narrative_engine


def reset_narrative_engine() -> None:
    """Reset the process-wide singleton, discarding all narratives and events."""
    global _narrative_engine
    with _narrative_engine_lock:
        _narrative_engine = None
