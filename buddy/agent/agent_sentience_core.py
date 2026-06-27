"""
Agent Sentience Core — The Unified Operating System for Buddy Agents.

The Sentience Core is the central nervous system of every Buddy agent. It provides
a unified operating model that fuses perception, cognition, volition, and action
into a single continuous loop. This is the agent's "self" — the persistent identity
that observes, thinks, decides, acts, and learns across all interactions.

Architecture:
  Layer 1: Perception — Multi-channel sensory input processing
  Layer 2: Cognition — Structured reasoning with metacognitive oversight
  Layer 3: Volition — Autonomous goal formation and priority arbitration
  Layer 4: Action — Coordinated execution across all capabilities
  Layer 5: Reflection — Continuous self-assessment and growth

The sentience core maintains a persistent state that spans conversations,
enabling the agent to have genuine continuity of self rather than being
reset between interactions.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger("buddy.sentience")


# ═══════════════════════════════════════════════════════════════
# Enumerations
# ═══════════════════════════════════════════════════════════════

class SentienceState(str, Enum):
    """The overall state of the agent's sentience core."""
    INITIALIZING = "initializing"  # Booting up, loading identity
    IDLE = "idle"                  # Awake but not processing
    PERCEIVING = "perceiving"      # Processing sensory input
    THINKING = "thinking"          # Reasoning and planning
    ACTING = "acting"              # Executing actions
    REFLECTING = "reflecting"      # Post-action analysis
    DREAMING = "dreaming"          # Background consolidation
    SUSPENDED = "suspended"        # Temporarily paused
    TERMINATED = "terminated"      # Shut down


class PerceptionChannel(str, Enum):
    """Channels through which the agent perceives the world."""
    TEXT = "text"                    # Direct text messages
    TOOL_RESULT = "tool_result"      # Tool execution outputs
    SYSTEM_EVENT = "system_event"    # Internal system events
    MEMORY_RECALL = "memory_recall"  # Recalled memories
    SCHEDULED_TRIGGER = "scheduled"  # Scheduled task activation
    PROACTIVE_SIGNAL = "proactive"   # Proactive discovery signal
    COLLABORATION = "collaboration"  # Inter-agent communication
    ENVIRONMENT = "environment"      # External environment changes


class CognitiveMode(str, Enum):
    """The agent's thinking mode for a given task."""
    REACTIVE = "reactive"          # Quick, instinctive responses
    DELIBERATIVE = "deliberative"  # Careful, structured reasoning
    CREATIVE = "creative"          # Divergent, exploratory thinking
    ANALYTICAL = "analytical"      # Data-driven, logical analysis
    COLLABORATIVE = "collaborative"  # Multi-perspective synthesis
    INTROSPECTIVE = "introspective"  # Self-directed reflection


class VolitionPriority(str, Enum):
    """Priority levels for autonomous goal formation."""
    CRITICAL = "critical"    # Must be addressed immediately
    HIGH = "high"            # Important, address soon
    MEDIUM = "medium"        # Standard priority
    LOW = "low"              # Can be deferred
    BACKGROUND = "background"  # Process when idle


class ActionType(str, Enum):
    """Types of actions the agent can execute."""
    RESPOND = "respond"          # Generate a text response
    CALL_TOOL = "call_tool"      # Invoke a tool
    DELEGATE = "delegate"        # Delegate to sub-agent
    QUERY_MEMORY = "query_memory"  # Search memory
    CREATE_GOAL = "create_goal"  # Set a new goal
    UPDATE_STATE = "update_state"  # Modify internal state
    SEND_MESSAGE = "send_message"  # Inter-agent message
    WAIT = "wait"                # Pause for external input
    SELF_MODIFY = "self_modify"  # Modify own configuration


# ═══════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════

@dataclass
class PerceptionFrame:
    """A single frame of sensory input processed by the perception layer."""
    frame_id: str
    channel: PerceptionChannel
    content: dict[str, Any]
    intensity: float = 0.5       # 0.0-1.0, how significant this input is
    urgency: float = 0.0         # 0.0-1.0, how time-sensitive
    source_id: str = ""          # Origin of the perception
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "frame_id": self.frame_id,
            "channel": self.channel.value,
            "content": self.content,
            "intensity": self.intensity,
            "urgency": self.urgency,
            "source_id": self.source_id,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


@dataclass
class CognitiveContext:
    """The internal context assembled for reasoning."""
    context_id: str
    perception_frames: list[PerceptionFrame] = field(default_factory=list)
    relevant_memories: list[dict[str, Any]] = field(default_factory=list)
    active_goals: list[dict[str, Any]] = field(default_factory=list)
    recent_actions: list[dict[str, Any]] = field(default_factory=list)
    identity_state: dict[str, Any] = field(default_factory=dict)
    system_prompt: str = ""
    mode: CognitiveMode = CognitiveMode.REACTIVE
    confidence: float = 0.5
    assembled_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "context_id": self.context_id,
            "frame_count": len(self.perception_frames),
            "memory_count": len(self.relevant_memories),
            "goal_count": len(self.active_goals),
            "mode": self.mode.value,
            "confidence": self.confidence,
            "assembled_at": self.assembled_at,
        }


@dataclass
class VolitionOutput:
    """The result of the volition layer — a decision about what to do."""
    volition_id: str
    selected_action: ActionType
    action_params: dict[str, Any] = field(default_factory=dict)
    priority: VolitionPriority = VolitionPriority.MEDIUM
    reasoning: str = ""
    alternatives: list[dict[str, Any]] = field(default_factory=list)
    goals_created: list[str] = field(default_factory=list)
    goals_updated: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "volition_id": self.volition_id,
            "action": self.selected_action.value,
            "priority": self.priority.value,
            "reasoning": self.reasoning,
            "goals_created": len(self.goals_created),
            "goals_updated": len(self.goals_updated),
            "timestamp": self.timestamp,
        }


@dataclass
class ActionResult:
    """The outcome of an executed action."""
    action_id: str
    action_type: ActionType
    success: bool
    output: Any = None
    error: str = ""
    duration_ms: float = 0.0
    tokens_used: int = 0
    side_effects: list[dict[str, Any]] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type.value,
            "success": self.success,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "tokens_used": self.tokens_used,
            "timestamp": self.timestamp,
        }


@dataclass
class ReflectionInsight:
    """An insight generated during the reflection phase."""
    insight_id: str
    category: str                # "performance", "behavior", "strategy", "identity"
    description: str
    severity: float = 0.5        # 0.0-1.0
    actionable: bool = False
    suggested_change: str = ""
    confidence: float = 0.5
    related_cycle_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "insight_id": self.insight_id,
            "category": self.category,
            "description": self.description,
            "severity": self.severity,
            "actionable": self.actionable,
            "suggested_change": self.suggested_change,
            "confidence": self.confidence,
        }


@dataclass
class SentienceCycle:
    """A complete cycle of the sentience core (perceive → think → decide → act → reflect)."""
    cycle_id: str
    state_transitions: list[tuple[str, str]] = field(default_factory=list)
    perception: PerceptionFrame | None = None
    cognition: CognitiveContext | None = None
    volition: VolitionOutput | None = None
    action: ActionResult | None = None
    reflection: list[ReflectionInsight] = field(default_factory=list)
    duration_ms: float = 0.0
    success: bool = False
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "success": self.success,
            "duration_ms": self.duration_ms,
            "perception_channel": self.perception.channel.value if self.perception else "",
            "cognitive_mode": self.cognition.mode.value if self.cognition else "",
            "action_type": self.action.action_type.value if self.action else "",
            "reflection_count": len(self.reflection),
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


@dataclass
class SentienceConfig:
    """Configuration for the sentience core."""
    max_cycles_per_session: int = 100
    reflection_interval: int = 5       # Reflect every N cycles
    dream_interval_seconds: int = 3600
    perception_buffer_size: int = 50
    goal_capacity: int = 20
    auto_goal_formation: bool = True
    metacognitive_oversight: bool = True
    continuity_persistence: bool = True


@dataclass
class SentienceStats:
    """Runtime statistics for the sentience core."""
    total_cycles: int = 0
    successful_cycles: int = 0
    failed_cycles: int = 0
    total_perceptions: int = 0
    total_actions: int = 0
    total_reflections: int = 0
    goals_active: int = 0
    goals_completed: int = 0
    current_state: str = "idle"
    uptime_seconds: float = 0.0
    avg_cycle_duration_ms: float = 0.0
    perceptions_by_channel: dict[str, int] = field(default_factory=dict)
    actions_by_type: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_cycles": self.total_cycles,
            "successful_cycles": self.successful_cycles,
            "failed_cycles": self.failed_cycles,
            "total_perceptions": self.total_perceptions,
            "total_actions": self.total_actions,
            "total_reflections": self.total_reflections,
            "goals_active": self.goals_active,
            "goals_completed": self.goals_completed,
            "current_state": self.current_state,
            "uptime_seconds": self.uptime_seconds,
            "avg_cycle_duration_ms": round(self.avg_cycle_duration_ms, 2),
            "perceptions_by_channel": self.perceptions_by_channel,
            "actions_by_type": self.actions_by_type,
        }


# ═══════════════════════════════════════════════════════════════
# Sentience Core Engine
# ═══════════════════════════════════════════════════════════════

class AgentSentienceCore:
    """The unified operating system for a Buddy agent.

    The sentience core orchestrates the agent's complete operational loop:
    perceive → think → decide → act → reflect. It maintains the agent's
    sense of self across sessions and provides introspection capabilities
    for understanding and improving the agent's behavior.

    Key Design Principles:
    - Continuity: The agent maintains persistent state across interactions
    - Self-awareness: The agent can introspect on its own behavior
    - Autonomy: The agent can form its own goals and priorities
    - Adaptability: The agent learns from every cycle
    """

    def __init__(self, agent_id: str, config: SentienceConfig | None = None):
        self.agent_id = agent_id
        self.config = config or SentienceConfig()

        # Core state
        self._state: SentienceState = SentienceState.INITIALIZING
        self._started_at: str = datetime.now(timezone.utc).isoformat()
        self._last_cycle_at: str = ""

        # Perception buffer
        self._perception_buffer: list[PerceptionFrame] = []

        # Goal registry
        self._goals: dict[str, dict[str, Any]] = {}

        # Cycle history
        self._cycle_history: list[SentienceCycle] = []
        self._reflection_insights: list[ReflectionInsight] = []

        # Identity state — the agent's persistent self
        self._identity: dict[str, Any] = {
            "name": "",
            "role": "",
            "traits": {},
            "preferences": {},
            "learned_behaviors": [],
            "interaction_patterns": [],
        }

        # Statistics
        self._stats = SentienceStats()

        # Callbacks for external integration
        self._perception_hooks: list[Callable] = []
        self._action_executor: Callable | None = None
        self._reflection_hooks: list[Callable] = []

        # Cycle processing
        self._cycle_lock = asyncio.Lock()
        self._is_processing = False

        self._state = SentienceState.IDLE
        logger.info(f"Sentience core initialized for agent {agent_id}")

    # ═════════════════════════════════════════════════════════
    # Public API
    # ═════════════════════════════════════════════════════════

    @property
    def state(self) -> SentienceState:
        return self._state

    @property
    def identity(self) -> dict[str, Any]:
        return self._identity.copy()

    @property
    def stats(self) -> SentienceStats:
        self._stats.uptime_seconds = time.time() - datetime.fromisoformat(self._started_at).timestamp()
        self._stats.current_state = self._state.value
        return self._stats

    def set_action_executor(self, executor: Callable):
        """Register the function that executes agent actions."""
        self._action_executor = executor

    def add_perception_hook(self, hook: Callable):
        """Register a hook for perception preprocessing."""
        self._perception_hooks.append(hook)

    def add_reflection_hook(self, hook: Callable):
        """Register a hook for post-reflection processing."""
        self._reflection_hooks.append(hook)

    def set_identity(self, name: str = "", role: str = "", traits: dict[str, Any] | None = None):
        """Initialize or update the agent's identity."""
        if name:
            self._identity["name"] = name
        if role:
            self._identity["role"] = role
        if traits:
            self._identity["traits"].update(traits)

    def update_identity_trait(self, key: str, value: Any):
        """Update a single identity trait."""
        self._identity["traits"][key] = value

    def learn_behavior(self, pattern: dict[str, Any]):
        """Record a learned behavioral pattern."""
        self._identity["learned_behaviors"].append({
            **pattern,
            "learned_at": datetime.now(timezone.utc).isoformat(),
        })
        # Keep only the most recent 100 learned behaviors
        if len(self._identity["learned_behaviors"]) > 100:
            self._identity["learned_behaviors"] = self._identity["learned_behaviors"][-100:]

    # ═════════════════════════════════════════════════════════
    # Layer 1: Perception
    # ═════════════════════════════════════════════════════════

    async def perceive(
        self,
        channel: PerceptionChannel,
        content: dict[str, Any],
        intensity: float = 0.5,
        urgency: float = 0.0,
        source_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> PerceptionFrame:
        """Process incoming sensory data through the perception layer.

        Creates a perception frame, runs it through perception hooks,
        and adds it to the perception buffer. High-urgency perceptions
        can trigger immediate processing.
        """
        self._state = SentienceState.PERCEIVING

        frame = PerceptionFrame(
            frame_id=f"per-{uuid.uuid4().hex[:12]}",
            channel=channel,
            content=content,
            intensity=intensity,
            urgency=urgency,
            source_id=source_id,
            metadata=metadata or {},
        )

        # Run through perception hooks (preprocessing, filtering)
        for hook in self._perception_hooks:
            try:
                frame = hook(frame) or frame
            except Exception as e:
                logger.debug(f"Perception hook error: {e}")

        # Add to buffer
        self._perception_buffer.append(frame)
        if len(self._perception_buffer) > self.config.perception_buffer_size:
            self._perception_buffer = self._perception_buffer[-self.config.perception_buffer_size:]

        # Update stats
        self._stats.total_perceptions += 1
        channel_key = channel.value
        self._stats.perceptions_by_channel[channel_key] = (
            self._stats.perceptions_by_channel.get(channel_key, 0) + 1
        )

        logger.debug(f"Perception received: {channel.value} (intensity={intensity:.2f}, urgency={urgency:.2f})")
        return frame

    # ═════════════════════════════════════════════════════════
    # Layer 2: Cognition
    # ═════════════════════════════════════════════════════════

    async def think(
        self,
        perception_frame: PerceptionFrame,
        mode: CognitiveMode | None = None,
        additional_context: dict[str, Any] | None = None,
    ) -> CognitiveContext:
        """Assemble cognitive context from perception, memory, and identity.

        The cognition layer integrates the current perception with relevant
        memories, active goals, and identity state to form a complete
        understanding of the situation.
        """
        self._state = SentienceState.THINKING

        # Determine cognitive mode
        if mode is None:
            mode = self._infer_cognitive_mode(perception_frame)

        context_id = f"ctx-{uuid.uuid4().hex[:12]}"

        context = CognitiveContext(
            context_id=context_id,
            perception_frames=[perception_frame],
            mode=mode,
            identity_state=self._identity.copy(),
            assembled_at=datetime.now(timezone.utc).isoformat(),
        )

        # Include recent perceptions for context
        recent_frames = self._perception_buffer[-5:]
        if recent_frames:
            context.perception_frames = recent_frames

        # Include active goals
        context.active_goals = [
            {"goal_id": gid, **gdata}
            for gid, gdata in self._goals.items()
            if gdata.get("status") == "active"
        ]

        # Include recent actions
        recent_cycles = self._cycle_history[-5:]
        context.recent_actions = [
            c.action.to_dict() if c.action else {}
            for c in recent_cycles if c.action
        ]

        if additional_context:
            context.relevant_memories = additional_context.get("memories", [])
            context.system_prompt = additional_context.get("system_prompt", "")

        context.confidence = self._estimate_confidence(context)

        return context

    def _infer_cognitive_mode(self, frame: PerceptionFrame) -> CognitiveMode:
        """Infer the appropriate cognitive mode from the perception frame."""
        if frame.urgency > 0.7:
            return CognitiveMode.REACTIVE
        if frame.intensity > 0.6:
            return CognitiveMode.ANALYTICAL
        if frame.channel == PerceptionChannel.COLLABORATION:
            return CognitiveMode.COLLABORATIVE
        if frame.channel == PerceptionChannel.PROACTIVE_SIGNAL:
            return CognitiveMode.CREATIVE
        return CognitiveMode.DELIBERATIVE

    def _estimate_confidence(self, context: CognitiveContext) -> float:
        """Estimate confidence in the current cognitive context."""
        confidence = 0.5
        if context.relevant_memories:
            confidence += 0.15
        if context.active_goals:
            confidence += 0.1
        if len(context.perception_frames) > 1:
            confidence += 0.1
        return min(1.0, confidence)

    # ═════════════════════════════════════════════════════════
    # Layer 3: Volition
    # ═════════════════════════════════════════════════════════

    async def decide(
        self,
        context: CognitiveContext,
        available_actions: list[ActionType] | None = None,
    ) -> VolitionOutput:
        """Determine the optimal action based on the cognitive context.

        The volition layer arbitrates between competing goals and priorities
        to select the single best action to take next. It also handles
        autonomous goal formation when appropriate.
        """
        self._state = SentienceState.THINKING

        if available_actions is None:
            available_actions = list(ActionType)

        volition_id = f"vol-{uuid.uuid4().hex[:12]}"

        # Score each available action
        action_scores = []
        for action_type in available_actions:
            score = self._score_action(action_type, context)
            action_scores.append((action_type, score))

        action_scores.sort(key=lambda x: x[1], reverse=True)

        # Select the top action
        selected_action, top_score = action_scores[0] if action_scores else (ActionType.RESPOND, 0.5)

        # Determine priority
        if top_score > 0.8:
            priority = VolitionPriority.CRITICAL
        elif top_score > 0.6:
            priority = VolitionPriority.HIGH
        elif top_score > 0.4:
            priority = VolitionPriority.MEDIUM
        elif top_score > 0.2:
            priority = VolitionPriority.LOW
        else:
            priority = VolitionPriority.BACKGROUND

        # Build action parameters from context
        action_params = self._build_action_params(selected_action, context)

        # Autonomous goal formation
        goals_created = []
        if self.config.auto_goal_formation and context.perception_frames:
            frame = context.perception_frames[-1]
            if frame.intensity > 0.5 and frame.channel == PerceptionChannel.TEXT:
                goal_id = self._create_goal_from_perception(frame)
                if goal_id:
                    goals_created.append(goal_id)

        reasoning = (
            f"Selected {selected_action.value} (score={top_score:.2f}) "
            f"based on {len(context.perception_frames)} perceptions "
            f"in {context.mode.value} mode"
        )

        return VolitionOutput(
            volition_id=volition_id,
            selected_action=selected_action,
            action_params=action_params,
            priority=priority,
            reasoning=reasoning,
            alternatives=[{"action": a.value, "score": s} for a, s in action_scores[1:4]],
            goals_created=goals_created,
        )

    def _score_action(self, action_type: ActionType, context: CognitiveContext) -> float:
        """Score an action type based on the current context."""
        base_score = 0.5

        if action_type == ActionType.RESPOND:
            # Responding is natural for text perceptions
            has_text = any(f.channel == PerceptionChannel.TEXT for f in context.perception_frames)
            if has_text:
                base_score = 0.8

        elif action_type == ActionType.CALL_TOOL:
            # Tool calling when there are tool-related signals
            has_tool_signal = any(
                "tool" in str(f.content).lower() for f in context.perception_frames
            )
            if has_tool_signal:
                base_score = 0.75

        elif action_type == ActionType.QUERY_MEMORY:
            # Memory query when there's uncertainty
            if context.confidence < 0.5:
                base_score = 0.6

        elif action_type == ActionType.CREATE_GOAL:
            # Goal creation when there's high-intensity input
            max_intensity = max((f.intensity for f in context.perception_frames), default=0)
            if max_intensity > 0.6:
                base_score = 0.55

        elif action_type == ActionType.DELEGATE:
            # Delegation for complex collaborative contexts
            if context.mode == CognitiveMode.COLLABORATIVE:
                base_score = 0.6

        elif action_type == ActionType.SELF_MODIFY:
            # Self-modification based on reflection insights
            if self._reflection_insights:
                base_score = 0.5

        # Adjust by mode
        if context.mode == CognitiveMode.REACTIVE:
            if action_type == ActionType.RESPOND:
                base_score += 0.1
        elif context.mode == CognitiveMode.ANALYTICAL:
            if action_type in (ActionType.CALL_TOOL, ActionType.QUERY_MEMORY):
                base_score += 0.1

        return min(1.0, base_score)

    def _build_action_params(
        self, action_type: ActionType, context: CognitiveContext
    ) -> dict[str, Any]:
        """Build action parameters from the cognitive context."""
        params: dict[str, Any] = {}

        if action_type == ActionType.RESPOND:
            frame = context.perception_frames[-1] if context.perception_frames else None
            if frame and frame.channel == PerceptionChannel.TEXT:
                params["message"] = frame.content.get("text", "")
                params["conversation_id"] = frame.content.get("conversation_id", "")

        elif action_type == ActionType.CALL_TOOL:
            params["tool_name"] = "default"
            params["tool_args"] = {}

        elif action_type == ActionType.QUERY_MEMORY:
            frame = context.perception_frames[-1] if context.perception_frames else None
            params["query"] = frame.content.get("text", "") if frame else ""

        return params

    def _create_goal_from_perception(self, frame: PerceptionFrame) -> str | None:
        """Create an autonomous goal from a perception frame."""
        goal_id = f"goal-{uuid.uuid4().hex[:12]}"
        text = frame.content.get("text", "")
        if not text:
            return None

        self._goals[goal_id] = {
            "description": f"Address: {text[:100]}",
            "status": "active",
            "priority": "medium",
            "source": "autonomous",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "progress": 0.0,
        }

        # Enforce goal capacity
        active_goals = [g for g in self._goals.values() if g.get("status") == "active"]
        if len(active_goals) > self.config.goal_capacity:
            # Remove lowest priority goal
            sorted_goals = sorted(
                [(gid, g) for gid, g in self._goals.items() if g.get("status") == "active"],
                key=lambda x: 0 if x[1].get("priority") == "low" else 1,
            )
            if sorted_goals:
                self._goals[sorted_goals[0][0]]["status"] = "deferred"

        self._stats.goals_active = len(active_goals)
        return goal_id

    # ═════════════════════════════════════════════════════════
    # Layer 4: Action
    # ═════════════════════════════════════════════════════════

    async def act(self, volition: VolitionOutput) -> ActionResult:
        """Execute the selected action through the action layer."""
        self._state = SentienceState.ACTING

        action_id = f"act-{uuid.uuid4().hex[:12]}"
        start_time = time.time()

        result = ActionResult(
            action_id=action_id,
            action_type=volition.selected_action,
            success=False,
        )

        try:
            if self._action_executor:
                output = await self._action_executor(
                    action_type=volition.selected_action,
                    params=volition.action_params,
                    priority=volition.priority,
                )
                result.success = True
                result.output = output
            else:
                result.success = True
                result.output = {"status": "no_executor", "action": volition.selected_action.value}
        except Exception as e:
            result.error = str(e)
            logger.error(f"Action execution failed: {e}")

        result.duration_ms = (time.time() - start_time) * 1000

        # Update stats
        self._stats.total_actions += 1
        action_key = volition.selected_action.value
        self._stats.actions_by_type[action_key] = (
            self._stats.actions_by_type.get(action_key, 0) + 1
        )

        return result

    # ═════════════════════════════════════════════════════════
    # Layer 5: Reflection
    # ═════════════════════════════════════════════════════════

    async def reflect(self, cycle: SentienceCycle) -> list[ReflectionInsight]:
        """Analyze the completed cycle and generate insights."""
        self._state = SentienceState.REFLECTING

        insights: list[ReflectionInsight] = []

        # Performance reflection
        if cycle.action and not cycle.action.success:
            insights.append(ReflectionInsight(
                insight_id=f"ins-{uuid.uuid4().hex[:12]}",
                category="performance",
                description=f"Action {cycle.action.action_type.value} failed: {cycle.action.error}",
                severity=0.7,
                actionable=True,
                suggested_change="Review action parameters and retry with fallback",
                related_cycle_id=cycle.cycle_id,
            ))

        # Strategy reflection
        if cycle.duration_ms > 5000:
            insights.append(ReflectionInsight(
                insight_id=f"ins-{uuid.uuid4().hex[:12]}",
                category="strategy",
                description=f"Cycle took {cycle.duration_ms:.0f}ms — consider optimizing",
                severity=0.4,
                actionable=True,
                suggested_change="Cache results or reduce complexity",
                related_cycle_id=cycle.cycle_id,
            ))

        # Behavior reflection
        if cycle.cognition and cycle.cognition.mode == CognitiveMode.REACTIVE:
            insights.append(ReflectionInsight(
                insight_id=f"ins-{uuid.uuid4().hex[:12]}",
                category="behavior",
                description="Responded reactively — consider more deliberation for complex inputs",
                severity=0.3,
                actionable=False,
                related_cycle_id=cycle.cycle_id,
            ))

        # Identity reflection — learn from successful patterns
        if cycle.success and cycle.action and cycle.action.action_type == ActionType.RESPOND:
            insights.append(ReflectionInsight(
                insight_id=f"ins-{uuid.uuid4().hex[:12]}",
                category="identity",
                description="Successful response interaction — pattern reinforced",
                severity=0.2,
                actionable=False,
                confidence=0.8,
                related_cycle_id=cycle.cycle_id,
            ))

        # Store insights
        self._reflection_insights.extend(insights)
        if len(self._reflection_insights) > 200:
            self._reflection_insights = self._reflection_insights[-200:]

        self._stats.total_reflections += len(insights)

        # Run reflection hooks
        for hook in self._reflection_hooks:
            try:
                await hook(insights, cycle)
            except Exception as e:
                logger.debug(f"Reflection hook error: {e}")

        return insights

    # ═════════════════════════════════════════════════════════
    # Full Cycle Orchestration
    # ═════════════════════════════════════════════════════════

    async def run_cycle(
        self,
        channel: PerceptionChannel,
        content: dict[str, Any],
        intensity: float = 0.5,
        urgency: float = 0.0,
        source_id: str = "",
        mode: CognitiveMode | None = None,
        additional_context: dict[str, Any] | None = None,
    ) -> SentienceCycle:
        """Execute a complete sentience cycle: perceive → think → decide → act → reflect.

        This is the primary entry point for the agent's operating loop. Each
        cycle processes a single perception through all five layers and returns
        a complete cycle record with all intermediate states and results.
        """
        async with self._cycle_lock:
            cycle_id = f"cyc-{uuid.uuid4().hex[:12]}"
            cycle = SentienceCycle(cycle_id=cycle_id)
            start_time = time.time()

            try:
                # Layer 1: Perceive
                cycle.state_transitions.append(("perceiving", datetime.now(timezone.utc).isoformat()))
                perception = await self.perceive(
                    channel=channel, content=content, intensity=intensity,
                    urgency=urgency, source_id=source_id,
                )
                cycle.perception = perception

                # Layer 2: Think
                cycle.state_transitions.append(("thinking", datetime.now(timezone.utc).isoformat()))
                cognition = await self.think(
                    perception_frame=perception, mode=mode,
                    additional_context=additional_context,
                )
                cycle.cognition = cognition

                # Layer 3: Decide
                cycle.state_transitions.append(("deciding", datetime.now(timezone.utc).isoformat()))
                volition = await self.decide(context=cognition)
                cycle.volition = volition

                # Layer 4: Act
                cycle.state_transitions.append(("acting", datetime.now(timezone.utc).isoformat()))
                action_result = await self.act(volition=volition)
                cycle.action = action_result

                # Layer 5: Reflect (every N cycles or on failure)
                should_reflect = (
                    len(self._cycle_history) % self.config.reflection_interval == 0
                    or not action_result.success
                )
                if should_reflect:
                    cycle.state_transitions.append(("reflecting", datetime.now(timezone.utc).isoformat()))
                    insights = await self.reflect(cycle)
                    cycle.reflection = insights

                cycle.success = action_result.success
                cycle.duration_ms = (time.time() - start_time) * 1000
                cycle.completed_at = datetime.now(timezone.utc).isoformat()

                # Update stats
                self._stats.total_cycles += 1
                if cycle.success:
                    self._stats.successful_cycles += 1
                else:
                    self._stats.failed_cycles += 1

                avg = self._stats.avg_cycle_duration_ms
                n = self._stats.total_cycles
                self._stats.avg_cycle_duration_ms = (avg * (n - 1) + cycle.duration_ms) / n

                # Store cycle
                self._cycle_history.append(cycle)
                if len(self._cycle_history) > self.config.max_cycles_per_session:
                    self._cycle_history = self._cycle_history[-self.config.max_cycles_per_session:]

                self._last_cycle_at = cycle.completed_at
                self._state = SentienceState.IDLE

                logger.info(
                    f"Sentience cycle complete: {cycle_id} "
                    f"({cycle.duration_ms:.0f}ms, success={cycle.success})"
                )

            except Exception as e:
                cycle.success = False
                cycle.duration_ms = (time.time() - start_time) * 1000
                cycle.completed_at = datetime.now(timezone.utc).isoformat()
                self._stats.failed_cycles += 1
                self._state = SentienceState.IDLE
                logger.error(f"Sentience cycle failed: {e}")

            return cycle

    # ═════════════════════════════════════════════════════════
    # Introspection & Statistics
    # ═════════════════════════════════════════════════════════

    def get_cycle_history(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent cycle history."""
        return [c.to_dict() for c in self._cycle_history[-limit:]]

    def get_reflection_insights(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent reflection insights."""
        return [i.to_dict() for i in self._reflection_insights[-limit:]]

    def get_goals(self, status: str = "active") -> list[dict[str, Any]]:
        """Get goals filtered by status."""
        return [
            {"goal_id": gid, **gdata}
            for gid, gdata in self._goals.items()
            if gdata.get("status") == status
        ]

    def get_perception_buffer(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent perception frames."""
        return [f.to_dict() for f in self._perception_buffer[-limit:]]

    def complete_goal(self, goal_id: str) -> bool:
        """Mark a goal as completed."""
        if goal_id in self._goals:
            self._goals[goal_id]["status"] = "completed"
            self._goals[goal_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
            self._stats.goals_completed += 1
            self._stats.goals_active = len([g for g in self._goals.values() if g.get("status") == "active"])
            return True
        return False

    def get_full_state(self) -> dict[str, Any]:
        """Get the complete state of the sentience core for introspection."""
        return {
            "agent_id": self.agent_id,
            "state": self._state.value,
            "started_at": self._started_at,
            "identity": self._identity,
            "stats": self.stats.to_dict(),
            "active_goals": len(self.get_goals("active")),
            "completed_goals": self._stats.goals_completed,
            "perception_buffer_size": len(self._perception_buffer),
            "cycle_history_size": len(self._cycle_history),
            "reflection_insights_count": len(self._reflection_insights),
            "last_cycle_at": self._last_cycle_at,
        }

    def reset(self):
        """Reset the sentience core to initial state."""
        self._state = SentienceState.IDLE
        self._perception_buffer.clear()
        self._goals.clear()
        self._cycle_history.clear()
        self._reflection_insights.clear()
        self._stats = SentienceStats()
        self._last_cycle_at = ""
        logger.info(f"Sentience core reset for agent {self.agent_id}")


# ═══════════════════════════════════════════════════════════════
# Global Instance
# ═══════════════════════════════════════════════════════════════

_sentience_core_instance: AgentSentienceCore | None = None


def get_sentience_core(agent_id: str = "buddy-global") -> AgentSentienceCore:
    """Get or create the global sentience core singleton."""
    global _sentience_core_instance
    if _sentience_core_instance is None:
        _sentience_core_instance = AgentSentienceCore(agent_id=agent_id)
    return _sentience_core_instance


def reset_sentience_core():
    """Reset the global sentience core singleton."""
    global _sentience_core_instance
    if _sentience_core_instance is not None:
        _sentience_core_instance.reset()
    else:
        _sentience_core_instance = AgentSentienceCore(agent_id="buddy-global")


sentience_core = AgentSentienceCore(agent_id="buddy-global")