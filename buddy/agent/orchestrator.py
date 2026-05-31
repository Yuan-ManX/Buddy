"""Multi-Agent Orchestrator for Buddy"""
from dataclasses import dataclass, field
from agent.engine import BuddyAgent

AGENT_POOL: dict[str, BuddyAgent] = {}


def get_or_create_agent(agent_id: str, name: str, personality: str, instructions: str) -> BuddyAgent:
    if agent_id not in AGENT_POOL:
        AGENT_POOL[agent_id] = BuddyAgent(agent_id, name, personality, instructions)
    else:
        agent = AGENT_POOL[agent_id]
        agent.name = name
        agent.personality = personality
        agent.instructions = instructions
    return AGENT_POOL[agent_id]


def remove_agent(agent_id: str):
    AGENT_POOL.pop(agent_id, None)


def clear_agent_context(agent_id: str):
    if agent_id in AGENT_POOL:
        AGENT_POOL[agent_id].clear_context()