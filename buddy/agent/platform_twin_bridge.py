"""Buddy Platform Twin Bridge — AI twin as intermediary and peer node

Connects the AI twin (agent_ai_twin.py) to the identity/persona system
and enables Bridge Mode: the twin acts as an intermediary between the
user and external systems, or between multi-agent teams.

Capabilities:
  - Bridge Mode: twin mediates between user and external APIs/agents,
    translating intent and filtering responses.
  - Peer Protocol: twins can communicate with each other in a
    permission-controlled peer network. Each twin stays independent.
  - Hierarchical Memory Modeling (HMM): three-tier memory — L0 (short-
    term interaction), L1 (mid-term context), L2 (long-term personalized
    cognition).
  - Identity Synthesis: combines twin state, persona, and identity core
    into a unified representation for cross-agent consistency.
"""
from __future__ import annotations

import logging
import threading
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger("buddy.platform.twin_bridge")


class MemoryTier(str, Enum):
    """Hierarchical Memory Modeling tiers."""
    L0_SHORT_TERM = "l0_short_term"    # Current interaction context
    L1_MID_TERM = "l1_mid_term"        # Session/recent context
    L2_LONG_TERM = "l2_long_term"      # Personalized persistent cognition


@dataclass
class TwinMemory:
    """A memory entry in the HMM structure."""
    memory_id: str = ""
    tier: MemoryTier = MemoryTier.L0_SHORT_TERM
    content: str = ""
    source: str = ""
    embedding: list[float] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    access_count: int = 0
    importance: float = 0.5

    def to_dict(self) -> dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "tier": self.tier.value,
            "content": self.content,
            "source": self.source,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "access_count": self.access_count,
            "importance": self.importance,
        }


@dataclass
class TwinIdentity:
    """Synthesized identity for cross-agent consistency."""
    twin_id: str = ""
    user_id: str = ""
    name: str = ""
    persona_traits: dict[str, float] = field(default_factory=dict)
    expertise_areas: list[str] = field(default_factory=list)
    communication_style: str = ""
    memory_l0: list[TwinMemory] = field(default_factory=list)
    memory_l1: list[TwinMemory] = field(default_factory=list)
    memory_l2: list[TwinMemory] = field(default_factory=list)
    connected_twins: list[str] = field(default_factory=list)
    bridge_targets: list[str] = field(default_factory=list)
    is_active: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "twin_id": self.twin_id,
            "user_id": self.user_id,
            "name": self.name,
            "persona_traits": self.persona_traits,
            "expertise_areas": self.expertise_areas,
            "communication_style": self.communication_style,
            "memory_counts": {
                "l0": len(self.memory_l0),
                "l1": len(self.memory_l1),
                "l2": len(self.memory_l2),
            },
            "connected_twins": self.connected_twins,
            "bridge_targets": self.bridge_targets,
            "is_active": self.is_active,
        }


class TwinBridge:
    """Manages AI twin Bridge Mode and peer-to-peer twin communication.

    The bridge enables twins to act as intermediaries and communicate
    with each other in a permission-controlled network. Each twin
    maintains its own HMM memory and synthesized identity.
    """

    def __init__(self):
        self._twins: dict[str, TwinIdentity] = {}
        self._peer_connections: dict[str, set[str]] = defaultdict(set)
        self._bridge_handlers: dict[str, Callable] = {}
        self._lock = threading.RLock()

    # ── Twin lifecycle ───────────────────────────────────

    def create_twin(
        self,
        user_id: str,
        name: str = "",
        persona_traits: Optional[dict[str, float]] = None,
        expertise_areas: Optional[list[str]] = None,
        communication_style: str = "",
    ) -> str:
        """Create a new AI twin with HMM memory structure."""
        twin_id = f"twin-{uuid.uuid4().hex[:12]}"
        twin = TwinIdentity(
            twin_id=twin_id,
            user_id=user_id,
            name=name or f"Twin-{twin_id[:8]}",
            persona_traits=persona_traits or {},
            expertise_areas=expertise_areas or [],
            communication_style=communication_style,
        )
        with self._lock:
            self._twins[twin_id] = twin
        logger.info("Created twin '%s' for user %s", twin.name, user_id)
        return twin_id

    def get_twin(self, twin_id: str) -> Optional[TwinIdentity]:
        with self._lock:
            return self._twins.get(twin_id)

    def list_twins(self, user_id: Optional[str] = None) -> list[dict[str, Any]]:
        with self._lock:
            twins = list(self._twins.values())
        if user_id:
            twins = [t for t in twins if t.user_id == user_id]
        return [t.to_dict() for t in twins]

    # ── HMM memory operations ────────────────────────────

    def add_memory(
        self,
        twin_id: str,
        tier: MemoryTier,
        content: str,
        source: str = "interaction",
        importance: float = 0.5,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Optional[str]:
        """Add a memory entry to a specific HMM tier."""
        with self._lock:
            twin = self._twins.get(twin_id)
            if twin is None:
                return None
            memory_id = f"mem-{uuid.uuid4().hex[:12]}"
            memory = TwinMemory(
                memory_id=memory_id,
                tier=tier,
                content=content,
                source=source,
                importance=importance,
                metadata=metadata or {},
            )
            if tier == MemoryTier.L0_SHORT_TERM:
                twin.memory_l0.append(memory)
                # L0 has a limited window
                if len(twin.memory_l0) > 50:
                    twin.memory_l0.pop(0)
            elif tier == MemoryTier.L1_MID_TERM:
                twin.memory_l1.append(memory)
                if len(twin.memory_l1) > 200:
                    twin.memory_l1.pop(0)
            else:
                twin.memory_l2.append(memory)
            return memory_id

    def search_memory(
        self,
        twin_id: str,
        query: str,
        tiers: Optional[list[MemoryTier]] = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Search across HMM tiers, prioritizing by tier and importance."""
        with self._lock:
            twin = self._twins.get(twin_id)
            if twin is None:
                return []

            all_memories: list[TwinMemory] = []
            if not tiers or MemoryTier.L0_SHORT_TERM in tiers:
                all_memories.extend(twin.memory_l0)
            if not tiers or MemoryTier.L1_MID_TERM in tiers:
                all_memories.extend(twin.memory_l1)
            if not tiers or MemoryTier.L2_LONG_TERM in tiers:
                all_memories.extend(twin.memory_l2)

        # Score by keyword match and importance
        query_lower = query.lower()
        scored: list[tuple[float, TwinMemory]] = []
        for mem in all_memories:
            content_lower = mem.content.lower()
            if query_lower in content_lower:
                score = 1.0 * mem.importance
            else:
                query_words = set(query_lower.split())
                content_words = set(content_lower.split())
                overlap = len(query_words & content_words)
                score = (overlap / max(1, len(query_words))) * mem.importance
            if score > 0:
                mem.access_count += 1
                scored.append((score, mem))

        # Tier priority: L2 > L1 > L0
        tier_priority = {MemoryTier.L2_LONG_TERM: 0, MemoryTier.L1_MID_TERM: 1, MemoryTier.L0_SHORT_TERM: 2}
        scored.sort(key=lambda x: (-x[0], tier_priority.get(x[1].tier, 99)))
        return [m.to_dict() for _, m in scored[:limit]]

    def promote_memory(self, twin_id: str, memory_id: str) -> bool:
        """Promote a memory from L0 → L1 → L2 based on importance."""
        with self._lock:
            twin = self._twins.get(twin_id)
            if twin is None:
                return False

            # Find the memory in any tier
            for tier_list, current_tier, next_tier in [
                (twin.memory_l0, MemoryTier.L0_SHORT_TERM, MemoryTier.L1_MID_TERM),
                (twin.memory_l1, MemoryTier.L1_MID_TERM, MemoryTier.L2_LONG_TERM),
            ]:
                for i, mem in enumerate(tier_list):
                    if mem.memory_id == memory_id:
                        tier_list.pop(i)
                        mem.tier = next_tier
                        if next_tier == MemoryTier.L1_MID_TERM:
                            twin.memory_l1.append(mem)
                        else:
                            twin.memory_l2.append(mem)
                        return True
            return False

    # ── Bridge Mode ──────────────────────────────────────

    def register_bridge_handler(
        self,
        target: str,
        handler: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> None:
        """Register a handler for a bridge target (external system/agent)."""
        with self._lock:
            self._bridge_handlers[target] = handler

    def bridge_request(
        self,
        twin_id: str,
        target: str,
        request: dict[str, Any],
    ) -> dict[str, Any]:
        """Use the twin as an intermediary to a bridge target.

        The twin translates the user's intent, sends it to the target,
        and filters the response before returning it.
        """
        with self._lock:
            twin = self._twins.get(twin_id)
            handler = self._bridge_handlers.get(target)

        if twin is None:
            return {"error": "Twin not found"}
        if handler is None:
            return {"error": f"Bridge target '{target}' has no handler"}

        # Record the bridge request in L0
        self.add_memory(
            twin_id, MemoryTier.L0_SHORT_TERM,
            f"Bridge request to {target}: {str(request)[:100]}",
            source="bridge",
        )

        try:
            response = handler(request)
            # Record the response in L0
            self.add_memory(
                twin_id, MemoryTier.L0_SHORT_TERM,
                f"Bridge response from {target}: {str(response)[:100]}",
                source="bridge",
            )
            return response
        except Exception as exc:
            logger.exception("Bridge request to %s failed: %s", target, exc)
            return {"error": str(exc)}

    # ── Peer Protocol ────────────────────────────────────

    def connect_twins(self, twin_id_a: str, twin_id_b: str) -> bool:
        """Establish a peer connection between two twins."""
        with self._lock:
            if twin_id_a not in self._twins or twin_id_b not in self._twins:
                return False
            self._peer_connections[twin_id_a].add(twin_id_b)
            self._peer_connections[twin_id_b].add(twin_id_a)
            self._twins[twin_id_a].connected_twins = list(self._peer_connections[twin_id_a])
            self._twins[twin_id_b].connected_twins = list(self._peer_connections[twin_id_b])
            return True

    def disconnect_twins(self, twin_id_a: str, twin_id_b: str) -> bool:
        with self._lock:
            self._peer_connections[twin_id_a].discard(twin_id_b)
            self._peer_connections[twin_id_b].discard(twin_id_a)
            if twin_id_a in self._twins:
                self._twins[twin_id_a].connected_twins = list(self._peer_connections[twin_id_a])
            if twin_id_b in self._twins:
                self._twins[twin_id_b].connected_twins = list(self._peer_connections[twin_id_b])
            return True

    def peer_message(
        self,
        from_twin_id: str,
        to_twin_id: str,
        message: str,
        message_type: str = "standard",
    ) -> dict[str, Any]:
        """Send a message from one twin to another via the peer protocol."""
        with self._lock:
            if to_twin_id not in self._peer_connections.get(from_twin_id, set()):
                return {"error": "Twins are not connected"}

            to_twin = self._twins.get(to_twin_id)
            if to_twin is None:
                return {"error": "Target twin not found"}

        # Record message in recipient's L0
        self.add_memory(
            to_twin_id, MemoryTier.L0_SHORT_TERM,
            f"Peer message from {from_twin_id}: {message[:200]}",
            source="peer",
            importance=0.7 if message_type == "important" else 0.5,
            metadata={"from_twin": from_twin_id, "message_type": message_type},
        )

        return {"status": "delivered", "to_twin": to_twin_id}

    # ── Identity synthesis ───────────────────────────────

    def synthesize_identity(self, twin_id: str) -> dict[str, Any]:
        """Synthesize a complete identity representation for cross-agent use.

        Combines twin state, persona traits, expertise, and memory
        summaries into a single identity object that other agents can
        use for consistent interaction.
        """
        with self._lock:
            twin = self._twins.get(twin_id)
            if twin is None:
                return {}

        # Summarize memories by tier
        l0_summary = " ".join(m.content[:50] for m in twin.memory_l0[-5:])
        l1_summary = " ".join(m.content[:50] for m in twin.memory_l1[-5:])
        l2_summary = " ".join(m.content[:50] for m in twin.memory_l2[-5:])

        return {
            "twin_id": twin.twin_id,
            "name": twin.name,
            "persona_traits": twin.persona_traits,
            "expertise_areas": twin.expertise_areas,
            "communication_style": twin.communication_style,
            "memory_summary": {
                "l0_recent": l0_summary,
                "l1_context": l1_summary,
                "l2_persistent": l2_summary,
            },
            "peer_count": len(twin.connected_twins),
            "bridge_targets": twin.bridge_targets,
            "is_active": twin.is_active,
        }

    # ── Stats ────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            total_memory = sum(
                len(t.memory_l0) + len(t.memory_l1) + len(t.memory_l2)
                for t in self._twins.values()
            )
            total_connections = sum(len(conns) for conns in self._peer_connections.values()) // 2
            return {
                "total_twins": len(self._twins),
                "active_twins": sum(1 for t in self._twins.values() if t.is_active),
                "total_memory_entries": total_memory,
                "peer_connections": total_connections,
                "bridge_handlers": len(self._bridge_handlers),
            }


# ═══════════════════════════════════════════════════════════
# Module-level singleton
# ═══════════════════════════════════════════════════════════

_twin_bridge: Optional[TwinBridge] = None
_tb_lock = threading.Lock()


def get_twin_bridge() -> TwinBridge:
    """Get the singleton TwinBridge instance."""
    global _twin_bridge
    if _twin_bridge is None:
        with _tb_lock:
            if _twin_bridge is None:
                _twin_bridge = TwinBridge()
    return _twin_bridge
