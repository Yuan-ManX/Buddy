#!/usr/bin/env python3
"""Comprehensive test of all API endpoints with correct paths"""
import requests
import sys

BASE = "http://localhost:8001/api"
results = {}

endpoints = [
    "/health",
    "/agents",
    "/agents/agent-strategy-001",
    "/orchestrator/stats",
    "/sentience-core/stats",
    "/capability-mesh/stats",
    "/presence-engine/stats",
    "/feedback-orchestrator/stats",
    "/session-commander/stats",
    "/runtime-scheduler/stats",
    "/workspace-nexus/stats",
    "/cognitive-engine/stats",
    "/platform-orchestrator/stats",
    "/skill-compiler/stats",
    "/runtime-store/stats",
    "/conversation-memory/stats",
    "/streaming-hub/stats",
    "/tool-network/stats",
    "/code-interpreter/stats",
    "/analytics-engine/stats",
    "/execution-compiler/stats",
    "/verification-pipeline/stats",
    "/model-conductor/stats",
    "/context-weaver/stats",
    "/autonomy-framework/stats",
    "/platform-hub/stats",
    "/adaptive-workflows/stats",
    "/cross-connector/stats",
    "/team-architect/stats",
    "/evolution-loop/stats",
    "/proactive-engine/stats",
    "/unified-system/stats",
    "/brain/stats",
    "/swarm/stats",
    "/subagent-mesh/stats",
    "/squads/stats",
    "/tool-composer/stats",
    "/self-improvement/stats",
    "/self-reflection/stats",
    "/profiles",
    "/protocol/stats",
    "/reasoning/stats",
    "/reflection/stats",
    "/synthesis/stats",
    "/runtimes-stats",
    "/sessions/stats",
    "/experiments/stats",
    "/white-memory/stats",
    "/trajectory/stats",
    "/user-model/stats",
    "/task-queue/stats",
    "/smart-router/stats",
    "/dream-mode/stats",
    "/autopilot/stats",
    "/mcp/stats",
    "/studio/stats",
    # New modules
    "/chain-of-thought/stats",
    "/intent-resolution/stats",
    "/dynamic-adaptation/stats",
    "/uncertainty-quantifier/stats",
    "/federated-knowledge/stats",
    "/emergent-behavior/stats",
    "/performance-autotuner/stats",
    "/platform-resilience/report",
]

for ep in endpoints:
    try:
        r = requests.get(f"{BASE}{ep}", timeout=10)
        status = "OK" if r.status_code < 400 else f"FAIL({r.status_code})"
        results[ep] = status
    except Exception as e:
        results[ep] = f"ERR: {str(e)[:60]}"

ok = sum(1 for v in results.values() if v == "OK")
fail = sum(1 for v in results.values() if v != "OK")
print(f"Total: {len(results)}, OK: {ok}, Fail: {fail}")
print()

if fail > 0:
    print("Failed endpoints:")
    for ep, status in sorted(results.items()):
        if status != "OK":
            print(f"  [{status}] {ep}")

print()
print("All OK endpoints:")
for ep, status in sorted(results.items()):
    if status == "OK":
        print(f"  [OK] {ep}")

sys.exit(0 if fail == 0 else 1)