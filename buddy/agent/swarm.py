"""Buddy Swarm — Dynamic agent team formation and cooperative execution

Enables agents to form ad-hoc teams (swarms) for complex tasks, with
role-based specialization, load balancing, and result aggregation.
"""
from __future__ import annotations
import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Awaitable

logger = logging.getLogger("buddy.swarm")


class SwarmRole(str, Enum):
    """Specialized roles within a swarm."""
    COORDINATOR = "coordinator"   # Manages task distribution and result synthesis
    RESEARCHER = "researcher"     # Gathers information and analyzes data
    ENGINEER = "engineer"         # Writes and executes code
    CRITIC = "critic"             # Reviews outputs and identifies issues
    CREATIVE = "creative"         # Generates ideas and alternatives
    EXECUTOR = "executor"         # Performs direct actions and tool calls


@dataclass
class SwarmMember:
    """A member of a swarm with role assignment and status tracking."""
    agent_id: str
    agent_name: str
    role: SwarmRole
    status: str = "idle"  # idle, working, done, failed
    task: str = ""
    result: str = ""
    tokens_used: int = 0
    started_at: str = ""
    completed_at: str = ""


@dataclass
class SwarmTask:
    """A task to be executed by a swarm."""
    id: str
    description: str
    required_roles: list[SwarmRole] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)  # task IDs that must complete first
    priority: int = 0
    status: str = "pending"  # pending, assigned, in_progress, done, failed


@dataclass
class SwarmSession:
    """An active swarm collaboration session."""
    id: str
    name: str
    goal: str
    members: list[SwarmMember] = field(default_factory=list)
    tasks: list[SwarmTask] = field(default_factory=list)
    results: list[dict] = field(default_factory=list)
    status: str = "forming"  # forming, planning, executing, reviewing, complete, failed
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str = ""


class SwarmEngine:
    """Manages dynamic agent team formation, task distribution, and cooperative execution.

    Agents self-organize into specialized roles based on their capabilities.
    Tasks flow through a dependency-aware pipeline with parallel execution
    where possible, and the coordinator synthesizes final results.
    """

    # Maximum concurrent tasks per swarm
    MAX_CONCURRENT_TASKS = 6

    def __init__(self):
        self._sessions: dict[str, SwarmSession] = {}
        self._agent_sessions: dict[str, list[str]] = {}  # agent_id -> [session_id, ...]
        self._chat_executors: dict[str, Callable] = {}  # session_id -> function to execute agent chats
        self._completion_callbacks: dict[str, list[Callable]] = {}  # session_id -> [callback, ...]

    def register_chat_executor(
        self,
        session_id: str,
        executor: Callable[[str, str, str], Awaitable[str]],
    ):
        """Register a function that executes agent chat (agent_id, prompt) -> response."""
        self._chat_executors[session_id] = executor

    def on_complete(self, session_id: str, callback: Callable[[SwarmSession], Awaitable[None]]):
        """Register a callback for swarm completion."""
        self._completion_callbacks.setdefault(session_id, []).append(callback)

    async def form_swarm(
        self,
        name: str,
        goal: str,
        available_agents: list[dict],
        min_members: int = 2,
    ) -> SwarmSession:
        """Form a new swarm from available agents based on the goal.

        Automatically assigns roles based on agent capabilities and the goal
        complexity analysis.
        """
        session_id = f"swarm-{uuid.uuid4().hex[:12]}"
        session = SwarmSession(id=session_id, name=name, goal=goal)

        # Analyze goal to determine required roles
        required_roles = self._analyze_goal_roles(goal)

        # Assign agents to roles based on their profiles
        assigned_agents: set[str] = set()
        for role in required_roles:
            best_agent = self._select_agent_for_role(available_agents, role, assigned_agents)
            if best_agent:
                member = SwarmMember(
                    agent_id=best_agent["id"],
                    agent_name=best_agent.get("name", best_agent["id"]),
                    role=role,
                )
                session.members.append(member)
                assigned_agents.add(best_agent["id"])
                self._agent_sessions.setdefault(best_agent["id"], []).append(session_id)

        if len(session.members) < min_members:
            logger.warning(f"Swarm '{name}' formed with only {len(session.members)} members (min: {min_members})")

        self._sessions[session_id] = session
        logger.info(f"Swarm '{name}' formed: {len(session.members)} members, {len(required_roles)} roles")
        return session

    async def plan_tasks(self, session_id: str) -> list[SwarmTask]:
        """Decompose the swarm goal into executable tasks."""
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Swarm session not found: {session_id}")

        session.status = "planning"

        # Decompose goal into structured tasks
        tasks = self._decompose_goal(session.goal, session.members)
        session.tasks = tasks

        logger.info(f"Swarm '{session.name}' planned {len(tasks)} tasks")
        return tasks

    async def execute(self, session_id: str) -> SwarmSession:
        """Execute all tasks in a swarm session with dependency-aware parallel execution."""
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Swarm session not found: {session_id}")

        if not session.tasks:
            await self.plan_tasks(session_id)

        session.status = "executing"
        executor = self._chat_executors.get(session_id)

        if not executor:
            raise ValueError(f"No chat executor registered for swarm session {session_id}")

        # Build dependency graph
        completed_tasks: set[str] = set()
        failed_tasks: set[str] = set()

        while len(completed_tasks) + len(failed_tasks) < len(session.tasks):
            # Find tasks ready for execution (dependencies satisfied)
            ready = []
            for task in session.tasks:
                if task.id in completed_tasks or task.id in failed_tasks:
                    continue
                if all(dep in completed_tasks for dep in task.dependencies):
                    ready.append(task)

            if not ready:
                # Circular dependency or all tasks complete
                break

            # Execute ready tasks in parallel batches
            batch = ready[:self.MAX_CONCURRENT_TASKS]
            batch_futures = []

            for task in batch:
                task.status = "in_progress"
                member = self._assign_member_for_task(task, session.members)
                if member:
                    member.status = "working"
                    member.task = task.id
                    member.started_at = datetime.now(timezone.utc).isoformat()
                    batch_futures.append(self._execute_task(task, member, executor, session))
                else:
                    task.status = "failed"
                    failed_tasks.add(task.id)

            # Wait for batch completion
            results = await asyncio.gather(*batch_futures, return_exceptions=True)

            for i, result in enumerate(results):
                task = batch[i]
                if isinstance(result, Exception):
                    task.status = "failed"
                    failed_tasks.add(task.id)
                    logger.error(f"Swarm task '{task.id}' failed: {result}")
                else:
                    task.status = "done"
                    completed_tasks.add(task.id)
                    session.results.append({
                        "task_id": task.id,
                        "description": task.description,
                        "result": result,
                        "completed_at": datetime.now(timezone.utc).isoformat(),
                    })

        # Synthesize final result from task outputs
        session.status = "reviewing"
        final_result = await self._synthesize_results(session, executor)
        session.results.append({
            "type": "synthesis",
            "content": final_result,
        })
        session.status = "complete"
        session.completed_at = datetime.now(timezone.utc).isoformat()

        # Trigger completion callbacks
        for callback in self._completion_callbacks.get(session_id, []):
            try:
                await callback(session)
            except Exception as e:
                logger.error(f"Swarm completion callback error: {e}")

        logger.info(f"Swarm '{session.name}' completed: {len(completed_tasks)}/{len(session.tasks)} tasks done")
        return session

    async def _execute_task(
        self,
        task: SwarmTask,
        member: SwarmMember,
        executor: Callable,
        session: SwarmSession,
    ) -> str:
        """Execute a single task within the swarm context."""
        # Build context from completed dependencies
        context = f"Swarm Goal: {session.goal}\n\nYour Role: {member.role.value}\n\nTask: {task.description}"

        # Include results from dependency tasks
        dep_results = [
            r for r in session.results
            if r.get("task_id") in task.dependencies
        ]
        if dep_results:
            context += "\n\n## Results from Previous Tasks:\n"
            for dr in dep_results:
                context += f"\n### {dr.get('task_id')}\n{dr.get('result', '')[:500]}"

        context += "\n\nComplete your assigned task. Be thorough and precise. Return your findings."

        try:
            result = await executor(member.agent_id, context, member.agent_name)
            member.status = "done"
            member.result = result
            member.completed_at = datetime.now(timezone.utc).isoformat()
            return result
        except Exception as e:
            member.status = "failed"
            member.result = str(e)
            member.completed_at = datetime.now(timezone.utc).isoformat()
            raise

    def _analyze_goal_roles(self, goal: str) -> list[SwarmRole]:
        """Determine required roles based on goal analysis."""
        goal_lower = goal.lower()
        roles = [SwarmRole.COORDINATOR]

        research_keywords = ["research", "analyze", "find", "search", "investigate", "study", "explore", "data"]
        engineering_keywords = ["code", "build", "develop", "implement", "deploy", "test", "debug", "api"]
        creative_keywords = ["design", "create", "brainstorm", "idea", "innovative", "novel", "creative"]
        critical_keywords = ["review", "audit", "security", "verify", "validate", "check", "quality"]

        if any(kw in goal_lower for kw in research_keywords):
            roles.append(SwarmRole.RESEARCHER)
        if any(kw in goal_lower for kw in engineering_keywords):
            roles.append(SwarmRole.ENGINEER)
        if any(kw in goal_lower for kw in creative_keywords):
            roles.append(SwarmRole.CREATIVE)
        if any(kw in goal_lower for kw in critical_keywords):
            roles.append(SwarmRole.CRITIC)

        # Always include at least one executor
        if SwarmRole.ENGINEER not in roles:
            roles.append(SwarmRole.EXECUTOR)

        return roles

    def _select_agent_for_role(
        self,
        agents: list[dict],
        role: SwarmRole,
        excluded: set[str],
    ) -> dict | None:
        """Select the best available agent for a given role."""
        role_affinity = {
            SwarmRole.RESEARCHER: ["research", "researcher", "analyst"],
            SwarmRole.ENGINEER: ["engineering", "engineer", "code", "developer"],
            SwarmRole.CREATIVE: ["creative", "designer", "companion"],
            SwarmRole.CRITIC: ["strategy", "strategist", "analyst"],
            SwarmRole.EXECUTOR: ["engineering", "engineer", "code"],
            SwarmRole.COORDINATOR: ["strategy", "strategist", "companion"],
        }

        preferred_roles = role_affinity.get(role, [])

        available = [a for a in agents if a["id"] not in excluded]

        # Score each agent by role fit
        scored = []
        for agent in available:
            agent_role = agent.get("role", "").lower()
            score = 0
            if any(pr in agent_role for pr in preferred_roles):
                score = 3
            elif agent_role in [r.lower() for r in preferred_roles]:
                score = 2
            else:
                score = 1
            scored.append((score, agent))

        scored.sort(key=lambda x: -x[0])
        return scored[0][1] if scored else None

    def _decompose_goal(self, goal: str, members: list[SwarmMember]) -> list[SwarmTask]:
        """Decompose the swarm goal into structured, dependency-aware tasks."""
        tasks = []
        role_set = {m.role for m in members}

        # Information gathering phase (parallel, no deps)
        if SwarmRole.RESEARCHER in role_set:
            tasks.append(SwarmTask(
                id=f"task-{uuid.uuid4().hex[:8]}",
                description=f"Research and gather information related to: {goal}",
                required_roles=[SwarmRole.RESEARCHER],
                priority=10,
            ))

        # Analysis phase (depends on research)
        if SwarmRole.CRITIC in role_set:
            analysis_task = SwarmTask(
                id=f"task-{uuid.uuid4().hex[:8]}",
                description=f"Analyze and evaluate approaches for: {goal}",
                required_roles=[SwarmRole.CRITIC],
                priority=8,
            )
            if tasks:
                analysis_task.dependencies = [tasks[0].id]
            tasks.append(analysis_task)

        # Creative generation phase (depends on research, parallel with analysis)
        if SwarmRole.CREATIVE in role_set:
            creative_task = SwarmTask(
                id=f"task-{uuid.uuid4().hex[:8]}",
                description=f"Generate innovative ideas and approaches for: {goal}",
                required_roles=[SwarmRole.CREATIVE],
                priority=7,
            )
            if tasks:
                creative_task.dependencies = [tasks[0].id]
            tasks.append(creative_task)

        # Implementation phase (depends on analysis and creative)
        exec_roles = [r for r in [SwarmRole.ENGINEER, SwarmRole.EXECUTOR] if r in role_set]
        if exec_roles:
            exec_task = SwarmTask(
                id=f"task-{uuid.uuid4().hex[:8]}",
                description=f"Implement the solution for: {goal}",
                required_roles=exec_roles,
                priority=5,
            )
            exec_task.dependencies = [t.id for t in tasks if t.id != tasks[0].id] if len(tasks) > 1 else []
            tasks.append(exec_task)
        elif tasks:
            # Default execution task
            exec_task = SwarmTask(
                id=f"task-{uuid.uuid4().hex[:8]}",
                description=f"Execute and deliver results for: {goal}",
                required_roles=[SwarmRole.COORDINATOR],
                priority=5,
            )
            if len(tasks) > 1:
                exec_task.dependencies = [t.id for t in tasks if t.id != tasks[0].id]
            tasks.append(exec_task)

        return tasks

    def _assign_member_for_task(
        self,
        task: SwarmTask,
        members: list[SwarmMember],
    ) -> SwarmMember | None:
        """Assign the best available member for a task."""
        for role in task.required_roles:
            for member in members:
                if member.role == role and member.status == "idle":
                    return member
        # Fallback: assign any idle member
        for member in members:
            if member.status == "idle":
                return member
        return None

    async def _synthesize_results(self, session: SwarmSession, executor: Callable) -> str:
        """Synthesize all task results into a final coherent output."""
        coordinator = next(
            (m for m in session.members if m.role == SwarmRole.COORDINATOR),
            session.members[0] if session.members else None,
        )

        if not coordinator:
            return "No coordinator available for synthesis."

        task_results = [
            r for r in session.results
            if r.get("task_id") and r.get("result")
        ]

        if not task_results:
            return "No task results to synthesize."

        synthesis_prompt = (
            f"Swarm Goal: {session.goal}\n\n"
            f"Below are results from {len(task_results)} tasks executed by the swarm. "
            f"Synthesize these into a single comprehensive, well-structured answer.\n\n"
        )
        for i, tr in enumerate(task_results):
            synthesis_prompt += (
                f"## Task {i+1}: {tr.get('description', tr['task_id'])}\n"
                f"{tr['result'][:1000]}\n\n"
            )
        synthesis_prompt += (
            "Provide a complete, synthesized response that integrates all findings. "
            "Use clear headings, bullet points, and structured formatting."
        )

        try:
            return await executor(coordinator.agent_id, synthesis_prompt, coordinator.agent_name)
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return f"Synthesis failed: {str(e)}"

    def get_session(self, session_id: str) -> SwarmSession | None:
        return self._sessions.get(session_id)

    def get_agent_sessions(self, agent_id: str) -> list[dict]:
        session_ids = self._agent_sessions.get(agent_id, [])
        return [
            {
                "id": sid,
                "name": self._sessions[sid].name,
                "status": self._sessions[sid].status,
            }
            for sid in session_ids
            if sid in self._sessions
        ]

    def list_sessions(self) -> list[dict]:
        return [
            {
                "session_id": s.id,
                "name": s.name,
                "goal": s.goal[:200],
                "members": [
                    {"agent_id": m.agent_id, "agent_name": m.agent_name, "role": m.role.value, "status": m.status}
                    for m in s.members
                ],
                "tasks": [
                    {"id": t.id, "description": t.description, "status": t.status, "priority": t.priority,
                     "required_roles": [r.value for r in t.required_roles], "dependencies": t.dependencies}
                    for t in s.tasks
                ],
                "results": s.results,
                "status": s.status,
                "created_at": s.created_at,
                "completed_at": s.completed_at,
            }
            for s in self._sessions.values()
        ]

    def get_stats(self) -> dict:
        sessions = list(self._sessions.values())
        return {
            "total_sessions": len(sessions),
            "active_sessions": sum(1 for s in sessions if s.status in ("forming", "planning", "executing")),
            "completed_sessions": sum(1 for s in sessions if s.status == "complete"),
            "failed_sessions": sum(1 for s in sessions if s.status == "failed"),
            "average_members": (
                sum(len(s.members) for s in sessions) / max(len(sessions), 1)
            ),
        }