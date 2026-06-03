"""Buddy Shared Agent Instances — singleton orchestrator and skills registry"""
from agent.orchestrator import Orchestrator
from agent.skills import SkillsRegistry

orchestrator = Orchestrator()
skills_registry = SkillsRegistry()