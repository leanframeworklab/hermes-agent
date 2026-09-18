"""Supported setup and observation helpers for durable runtime benchmarks."""

from dataclasses import dataclass
from typing import Any

from agent.context_compiler import ContextMetrics
from agent.durable_mission import CHECKPOINT_SCHEMA_VERSION, MissionCheckpoint


@dataclass(frozen=True)
class DurableBenchmarkSetup:
    mission: dict[str, Any]
    checkpoint: MissionCheckpoint
    session_binding: dict[str, str]


@dataclass(frozen=True)
class BenchmarkTurnObservation:
    turn_number: int
    metrics: ContextMetrics | None
    mission_id: str
    session_id: str
    checkpoint_before: MissionCheckpoint
    checkpoint_after: MissionCheckpoint
    provider_invoked: bool
    result: Any


def create_durable_benchmark_mission(
    session_db,
    mission_id: str,
    session_id: str,
    objective: str,
    next_action: str,
) -> DurableBenchmarkSetup:
    """Create benchmark P1 state through SessionDB's public APIs."""
    session_db.create_session(session_id, "benchmark")
    session_db.create_mission(mission_id, root_session_id=session_id)
    checkpoint = MissionCheckpoint(
        mission_id=mission_id,
        checkpoint_id=f"{mission_id}:checkpoint:0",
        parent_checkpoint_id=None,
        state_version=CHECKPOINT_SCHEMA_VERSION,
        objective=objective,
        phase="benchmark",
        pending_steps=[next_action],
        next_action=next_action,
        status="ACTIVE",
    )
    session_db.write_mission_checkpoint(checkpoint)
    binding = session_db.get_mission_for_session(session_id)
    if binding is None or binding["mission_id"] != mission_id:
        raise RuntimeError("benchmark session is not bound to durable mission")
    return DurableBenchmarkSetup(
        mission=session_db.get_mission(mission_id),
        checkpoint=session_db.load_mission_checkpoint(mission_id),
        session_binding={"mission_id": mission_id, "session_id": session_id},
    )


class DurableBenchmarkHarness:
    """Run complete agent turns and read public telemetry after each turn."""

    def __init__(self, agent, session_db, mission_id: str):
        self.agent = agent
        self.session_db = session_db
        self.mission_id = mission_id
        self.turn_number = 0

    def run_turn(self, user_message: str) -> BenchmarkTurnObservation:
        session_id = self.agent.session_id
        before = self.session_db.load_mission_checkpoint(self.mission_id)
        result = self.agent.run_conversation(user_message)
        metrics = self.agent.get_context_metrics()
        after = self.session_db.load_mission_checkpoint(self.mission_id)
        self.turn_number += 1
        provider_invoked = bool(
            result.get(
                "provider_invoked",
                result.get("api_calls", 0) > 0 or result.get("completed", False),
            )
            if isinstance(result, dict)
            else True
        )
        return BenchmarkTurnObservation(
            turn_number=self.turn_number,
            metrics=metrics,
            mission_id=self.mission_id,
            session_id=session_id,
            checkpoint_before=before,
            checkpoint_after=after,
            provider_invoked=provider_invoked,
            result=result,
        )
