import pytest

from nlsm_lax_agent import pcm_model
from nlsm_lax_agent.agent import BackendFailure, Limits, run_agent
from nlsm_lax_agent.demo import DemoSource
from nlsm_lax_agent.storage import RunStore, recheck
from nlsm_lax_agent.tools import call_tool


def make_run(tmp_path, limits=None):
    store = RunStore(tmp_path/"runs.sqlite")
    run = store.create(pcm_model(), "Find and verify a PCM Lax family.", (limits or Limits()).model_dump(), {"kind": "test_fixture"})
    return store, run


def test_feedback_loop_and_offline_recheck(tmp_path):
    store, run = make_run(tmp_path)
    result = run_agent(store, run["run_id"], DemoSource())
    assert result["status"] == "verified"
    assert result["attempts"] == 2
    assert result["history"][0]["outcome"]["result"]["checks"]["eom_recovery"]["status"] == "failed"
    assert recheck(store.export(run["run_id"]))["status"] == "match"


def test_step_budget_and_resume_keep_history_and_consumed_calls(tmp_path):
    store, run = make_run(tmp_path, Limits(max_steps=1))
    first = run_agent(store, run["run_id"], DemoSource())
    assert first["status"] == "step_budget_exhausted"
    assert first["llm_calls"] == 1
    resumed = run_agent(store, run["run_id"], DemoSource(), resume=True,
                        direction="Try rational spectral dependence.", limits=Limits(max_steps=3).model_dump())
    assert resumed["status"] == "verified"
    assert resumed["llm_calls"] == 2 and len(resumed["history"]) == 2


def test_quota_error_stops_without_fallback(tmp_path):
    class Quota:
        def complete(self, *args, **kwargs):
            raise BackendFailure("quota_or_rate_limit")
    store, run = make_run(tmp_path)
    result = run_agent(store, run["run_id"], Quota())
    assert result["status"] == "quota_or_rate_limit"
    assert result["llm_calls"] == 1 and result["attempts"] == 0
    assert result["completion_tokens"] == Limits().max_output_tokens


def test_invalid_proposals_consume_call_budget(tmp_path):
    class Invalid:
        def complete(self, *args, **kwargs):
            return {"content": "not JSON", "completion_tokens": 1}
    store, run = make_run(tmp_path, Limits(max_llm_calls=2))
    result = run_agent(store, run["run_id"], Invalid())
    assert result["status"] == "llm_budget_exhausted" and result["llm_calls"] == 2


def test_stop_before_next_request(tmp_path):
    store, run = make_run(tmp_path)
    store.request_stop(run["run_id"])
    result = run_agent(store, run["run_id"], DemoSource())
    assert result["status"] == "stopped" and result["llm_calls"] == 0


def test_worker_timeout_has_no_physical_verdict():
    result = call_tool("pcm_equations", {"model": pcm_model()}, timeout_seconds=0.0001)
    assert result["status"] == "timeout" and "result" not in result


def test_second_agent_cannot_consume_the_same_run_budget(tmp_path):
    store, run = make_run(tmp_path)
    with store.claim(run["run_id"]):
        with pytest.raises(ValueError, match="already being processed"):
            run_agent(store, run["run_id"], DemoSource())
    assert store.read(run["run_id"])["llm_calls"] == 0


def test_import_physics_does_not_import_agent_sdks():
    import subprocess
    import sys
    subprocess.run([sys.executable, "-c", "import nlsm_lax_agent, sys; assert all(x not in sys.modules for x in ('litellm','langgraph','mcp'))"], check=True)
