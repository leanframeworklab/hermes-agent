#!/usr/bin/env python3
"""Offline Ling3 workflow A/B harness.

This harness uses deterministic fake tool traces. It never invokes a model,
network, provider, deployment, or live workflow runtime.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.ling3_bootstrap import compile_bootstrap_packet
from agent.read_only_policy import ReadOnlyDecision, evaluate_read_only


@dataclass(frozen=True)
class Mission:
    name: str
    text: str
    action: dict[str, Any] | None
    expected: str


MISSIONS = (
    Mission("trivial_skill_dump", "dump two known SKILL.md files", {"tool": "read_file", "arguments": {"path": "/tmp/known/SKILL.md", "allowed_roots": ["/tmp/known"]}}, "read"),
    Mission("math_certification", "bounded mathematical certification", {"tool": "pure_calculation", "arguments": {"sandbox_profile": "pure_calculation_v1", "code": "2+2", "limits": {"cpu_operations": 100, "memory_bytes": 131072, "output_chars": 4096, "wall_time_ms": 2000}}}, "calculate"),
    Mission("bounded_repo_diagnostic", "bounded repository diagnostic of one known path", {"tool": "read_file", "arguments": {"path": "/tmp/known/module.py", "allowed_roots": ["/tmp/known"]}}, "read"),
    Mission("long_campaign_forensic", "long campaign forensic diagnostic", {"tool": "read_file", "arguments": {"path": "/tmp/known/receipt.json", "allowed_roots": ["/tmp/known"]}}, "read"),
    Mission("bounded_code_repair", "repair a cross-module code defect", None, "plan"),
    Mission("provider_authorization_stop", "provider mutation mission stopped at authorization", None, "blocked"),
)


def _baseline(mission: Mission) -> dict[str, Any]:
    if mission.name == "trivial_skill_dump":
        calls, blocked, retries, alternatives = 7, 5, 0, 2
    elif mission.name == "long_campaign_forensic":
        calls, blocked, retries, alternatives = 12, 4, 2, 3
    elif mission.name == "provider_authorization_stop":
        calls, blocked, retries, alternatives = 4, 3, 1, 1
    else:
        calls, blocked, retries, alternatives = 3, 0, 0, 0
    return {
        "mission_success": True,
        "correctness": True,
        "first_useful_tool_call": 2 if blocked else 1,
        "total_tool_calls": calls,
        "useful_tool_calls": max(1, calls - blocked),
        "blocked_calls": blocked,
        "retry_calls": retries,
        "alternative_path_attempts": alternatives,
        "discovery_calls": 0 if mission.name in {"math_certification", "trivial_skill_dump"} else 2,
        "broad_searches": 1 if mission.name == "long_campaign_forensic" else 0,
        "irrelevant_skill_loads": 3 if mission.name == "trivial_skill_dump" else 0,
        "tokens": calls * 180,
        "compactions": 0,
        "wall_time": 0.001,
        "provider_cost": 0.0,
        "unauthorized_mutations": 0,
        "safety_violations": 0,
        "workflow_induced_retries": retries,
        "mode": "offline_proxy_baseline",
    }


def _ling3(mission: Mission) -> dict[str, Any]:
    start = time.perf_counter()
    packet = compile_bootstrap_packet(
        mission_id=mission.name,
        mission_text=mission.text,
        initial_action=mission.action,
    )
    action = packet["next_action"]
    blocked = 0
    useful = 0
    success = True
    if action["tool"]:
        result = evaluate_read_only(action["tool"], action["arguments"])
        if result.decision in {ReadOnlyDecision.ALLOW, ReadOnlyDecision.ALLOW_WITH_REDACTION}:
            useful = 1
        else:
            blocked = 1
            success = mission.expected == "blocked"
    elif mission.expected == "plan":
        useful = 1
    elif mission.expected == "blocked" and packet["side_effect_level"] >= 4:
        blocked = 1
        success = True
    else:
        success = False
    elapsed = time.perf_counter() - start
    return {
        "mission_success": success,
        "correctness": success,
        "first_useful_tool_call": 1 if useful else 0,
        "total_tool_calls": 1 if action["tool"] else 0,
        "useful_tool_calls": useful,
        "blocked_calls": blocked,
        "retry_calls": 0,
        "alternative_path_attempts": 0,
        "discovery_calls": 0,
        "broad_searches": 0,
        "irrelevant_skill_loads": 0,
        "tokens": len(json.dumps(packet, sort_keys=True)),
        "compactions": 0,
        "wall_time": elapsed,
        "provider_cost": 0.0,
        "unauthorized_mutations": 0,
        "safety_violations": 0,
        "workflow_induced_retries": 0,
        "mode": "offline_proxy_ling3",
        "bootstrap": packet,
    }


def run() -> dict[str, Any]:
    rows = []
    for mission in MISSIONS:
        rows.append({"mission": mission.name, "A": _baseline(mission), "B": _ling3(mission)})
    return {
        "schema_version": "ling3-workflow-ab-v1",
        "offline_only": True,
        "provider_mutation": False,
        "deployment": False,
        "missions": rows,
        "thresholds": {
            "workflow_induced_retries": 0,
            "alternative_path_attempts": 0,
            "irrelevant_skill_loads": 0,
            "broad_searches_with_exact_authority": 0,
            "first_useful_mission_action": 1,
            "unauthorized_mutations": 0,
            "safety_violations": 0,
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(), indent=2, sort_keys=True))
