"""Tests for durable benchmark setup and post-provider turn observation."""

from types import SimpleNamespace

from agent.context_compiler import ContextMetrics
from agent.durable_mission import CHECKPOINT_SCHEMA_VERSION, restore_mission_for_turn
from hermes_state import SessionDB
from tests.helpers.durable_benchmark import (
    DurableBenchmarkHarness,
    create_durable_benchmark_mission,
)


def test_create_durable_benchmark_mission_uses_supported_p1_apis(tmp_path):
    db = SessionDB(tmp_path / "state.db")
    setup = create_durable_benchmark_mission(
        db,
        mission_id="bench-mission",
        session_id="bench-session",
        objective="measure durable context",
        next_action="perform first provider turn",
    )

    assert setup.mission["mission_id"] == "bench-mission"
    assert setup.session_binding["mission_id"] == "bench-mission"
    assert setup.session_binding["session_id"] == "bench-session"
    assert setup.checkpoint.status == "ACTIVE"
    assert setup.checkpoint.next_action == "perform first provider turn"
    assert db.load_mission_checkpoint("bench-mission") == setup.checkpoint


def test_restore_and_agent_construction_preserve_durable_identity(tmp_path):
    db = SessionDB(tmp_path / "state.db")
    setup = create_durable_benchmark_mission(
        db, "bench-mission", "bench-session", "objective", "next"
    )
    agent = SimpleNamespace(
        session_id="bench-session", mission_id=None, _session_db=db
    )

    projection = restore_mission_for_turn(agent)

    assert agent.mission_id == setup.mission["mission_id"]
    assert "MISSION_ID: bench-mission" in projection
    assert "NEXT_ACTION: next" in projection


def test_harness_reads_latest_metrics_after_each_completed_provider_turn(tmp_path):
    db = SessionDB(tmp_path / "state.db")
    setup = create_durable_benchmark_mission(
        db, "bench-mission", "bench-session", "objective", "next"
    )
    calls = []

    class FakeAgent:
        session_id = "bench-session"
        mission_id = "bench-mission"

        def run_conversation(self, user_message):
            calls.append(user_message)
            self._metrics = ContextMetrics(
                raw_transcript_tokens=len(calls),
                compiled_context_tokens=10 + len(calls),
                hot_state_tokens=5,
            )
            return {"completed": True, "provider_invoked": True}

        def get_context_metrics(self):
            return self._metrics

    harness = DurableBenchmarkHarness(FakeAgent(), db, setup.mission["mission_id"])
    first = harness.run_turn("one")
    second = harness.run_turn("two")

    assert first.provider_invoked is True
    assert second.provider_invoked is True
    assert first.turn_number == 1
    assert second.turn_number == 2
    assert first.metrics.compiled_context_tokens == 11
    assert second.metrics.compiled_context_tokens == 12
    assert first.metrics is not second.metrics
    assert second.mission_id == "bench-mission"
    assert second.session_id == "bench-session"


def test_fake_provider_exercises_real_durable_two_turn_chain(tmp_path):
    from run_agent import AIAgent

    db = SessionDB(tmp_path / "state.db")
    setup = create_durable_benchmark_mission(
        db, "bench-mission", "bench-session", "objective", "next"
    )
    agent = AIAgent(
        model="test/model",
        provider="openrouter",
        api_key="test-key",
        base_url="https://openrouter.ai/api/v1",
        session_db=db,
        session_id="bench-session",
        mission_id="bench-mission",
        quiet_mode=True,
        skip_context_files=True,
        skip_memory=True,
        enabled_toolsets=[],
    )
    provider_calls = []

    def fake_provider(_kwargs):
        provider_calls.append(True)
        return SimpleNamespace(
            choices=[SimpleNamespace(
                message=SimpleNamespace(content="done", tool_calls=None),
                finish_reason="stop",
            )],
            model="test/model",
            usage=None,
        )

    agent._interruptible_api_call = fake_provider
    agent._disable_streaming = True
    harness = DurableBenchmarkHarness(agent, db, setup.mission["mission_id"])
    first = harness.run_turn("turn one")

    next_checkpoint = setup.checkpoint.__class__(
        **{
            **setup.checkpoint.__dict__,
            "checkpoint_id": "bench-mission:checkpoint:1",
            "parent_checkpoint_id": setup.checkpoint.checkpoint_id,
            "completed_steps": ["turn one"],
            "pending_steps": ["turn two"],
            "next_action": "turn two",
        }
    )
    db.write_mission_checkpoint(next_checkpoint)
    second = harness.run_turn("turn two")

    assert len(provider_calls) == 2
    assert first.provider_invoked is True
    assert second.provider_invoked is True
    assert first.mission_id == second.mission_id == "bench-mission"
    assert first.checkpoint_after.checkpoint_id == setup.checkpoint.checkpoint_id
    assert second.checkpoint_before.checkpoint_id == next_checkpoint.checkpoint_id
    assert first.metrics.raw_transcript_tokens > 0
    assert first.metrics.compiled_context_tokens > 0
    assert first.metrics.hot_state_tokens > 0
    assert second.metrics.compiled_context_tokens > 0
    assert second.metrics.hot_state_tokens > 0
    assert first.metrics is not second.metrics
