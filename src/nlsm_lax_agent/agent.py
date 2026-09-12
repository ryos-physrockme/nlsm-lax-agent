"""LangGraph propose/calculate/revise loop with a replaceable proposal source."""

import os
import multiprocessing as mp
import time
from typing import Annotated, Literal, Protocol, TypedDict
from urllib.parse import urlsplit

from pydantic import Field, ValidationError, model_validator

from .inputs import StrictModel
from .storage import RunStore, json_text, load_json
from .tools import REGISTRY, call_tool, list_tools


class Limits(StrictModel):
    max_steps: Annotated[int, Field(ge=1, le=100)] = 6
    max_llm_calls: Annotated[int, Field(ge=1, le=100)] = 6
    total_seconds: Annotated[float, Field(gt=0, le=3600)] = 300.0
    tool_seconds: Annotated[float, Field(gt=0, le=300)] = 30.0
    llm_seconds: Annotated[float, Field(gt=0, le=120)] = 60.0
    max_output_tokens: Annotated[int, Field(ge=64, le=8192)] = 2048
    total_output_tokens: Annotated[int, Field(ge=64, le=65536)] = 12288
    memory_mb: Annotated[int, Field(ge=128)] | None = None


class BackendConfig(StrictModel):
    kind: Literal["gemini", "local"]
    model: str
    api_base: str | None = None
    api_key_env: str = "GEMINI_API_KEY"
    json_mode: bool = False

    @model_validator(mode="after")
    def check_destination(self):
        if self.kind == "gemini":
            if not self.model.startswith("gemini/") or self.api_base is not None:
                raise ValueError("Gemini requires a gemini/ model and its standard endpoint.")
        else:
            url = urlsplit(self.api_base or "")
            if (not self.model.startswith("openai/") or url.scheme not in ("http", "https")
                    or url.hostname not in ("localhost", "127.0.0.1", "::1") or url.username or url.password
                    or url.query or url.fragment):
                raise ValueError("The local profile requires an openai/ model and a loopback API endpoint.")
        return self


class Action(StrictModel):
    tool: Annotated[str, Field(min_length=1, max_length=100)]
    arguments: dict
    reason: Annotated[str, Field(min_length=1, max_length=4000)]


class BackendFailure(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


class ProposalSource(Protocol):
    def complete(self, messages: list[dict], *, timeout: float, max_tokens: int) -> dict: ...


class LiteLLMSource:
    def __init__(self, config: BackendConfig):
        self.config = config

    def complete(self, messages, *, timeout, max_tokens):
        context = mp.get_context("spawn")
        reader, writer = context.Pipe(duplex=False)
        process = context.Process(target=_llm_worker, args=(writer, self.config.model_dump(), messages, timeout, max_tokens))
        process.start()
        writer.close()
        try:
            if not reader.poll(timeout):
                raise BackendFailure("llm_timeout")
            try:
                reply = reader.recv()
            except EOFError as exc:
                raise BackendFailure("llm_worker_failed") from exc
            if "error" in reply:
                raise BackendFailure(reply["error"])
            return reply["reply"]
        finally:
            if process.is_alive():
                process.terminate()
            process.join(timeout=2)
            if process.is_alive():
                process.kill()
                process.join()
            reader.close()

    def _complete(self, messages, *, timeout, max_tokens):
        # Import here: deterministic calculations and rechecks need no SDK.
        cfg = self.config
        key = os.environ.get(cfg.api_key_env) if cfg.kind == "gemini" else "local"
        if not key:
            raise BackendFailure("missing_api_key")
        import litellm
        kwargs = {"model": cfg.model, "api_key": key, "messages": messages,
                  "timeout": timeout, "max_tokens": max_tokens, "num_retries": 0,
                  "temperature": 0, "drop_params": False}
        if cfg.api_base:
            kwargs["api_base"] = cfg.api_base
        if cfg.json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        try:
            response = litellm.completion(**kwargs)
        except litellm.RateLimitError as exc:
            raise BackendFailure("quota_or_rate_limit") from exc
        except litellm.AuthenticationError as exc:
            raise BackendFailure("authentication_error") from exc
        except litellm.Timeout as exc:
            raise BackendFailure("llm_timeout") from exc
        except Exception as exc:
            raise BackendFailure("llm_connection_error") from exc
        usage = response.usage
        return {"content": response.choices[0].message.content or "",
                "prompt_tokens": getattr(usage, "prompt_tokens", 0) or 0,
                "completion_tokens": getattr(usage, "completion_tokens", None),
                "model": response.model, "response_id": response.id}


def _llm_worker(connection, config, messages, timeout, max_tokens):
    try:
        os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
        reply = LiteLLMSource(BackendConfig.model_validate(config))._complete(messages, timeout=timeout, max_tokens=max_tokens)
        connection.send({"reply": reply})
    except BackendFailure as exc:
        connection.send({"error": exc.code})
    except Exception:
        connection.send({"error": "llm_worker_failed"})
    finally:
        connection.close()


SYSTEM = """You assist with classical SU(2) principal chiral model Lax search.
Return exactly one JSON object: {"tool": "registered name", "arguments": {...}, "reason": "short ansatz rationale"}.
Choose a calculation, inspect its result, and revise the ansatz when it fails.
Use exact expression strings with *, /, **, integers and z (I is the imaginary unit).
Do not generate executable code. You may change coefficients and rational spectral functions within supported tools.
The model, run ID and revision are supplied by the host; omit those arguments.
The host alone decides verification from all three checks. Flatness alone is insufficient.
Tool failure or an empty coefficient solve does not establish model nonintegrability.
If no supported calculation can help, use tool="finish", arguments={}, and explain alternatives and limitations in reason.
The independent spectral parameter is z. It is distinct from the coupling kappa.
"""


class GraphState(TypedDict):
    run: dict


def _has_verified(outcome):
    if outcome.get("status") != "completed":
        return False
    result = outcome["result"]
    return result.get("status") == "verified" or any(
        candidate.get("verification", {}).get("status") == "verified" for candidate in result.get("candidates", []))


def run_agent(store: RunStore, run_id: str, source: ProposalSource, *, resume=False, direction=None, limits=None):
    with store.claim(run_id):
        return _run_agent(store, run_id, source, resume=resume, direction=direction, limits=limits)


def _run_agent(store, run_id, source, *, resume=False, direction=None, limits=None):
    from langgraph.graph import END, START, StateGraph

    run = store.read(run_id)
    if run["status"] == "verified":
        return run
    if resume:
        run["stop_requested"] = False
        if limits is not None:
            run["limits"] = Limits.model_validate(limits).model_dump()
        if direction:
            run["messages"].append({"role": "user", "content": f"Researcher direction: {direction}"})
        run["status"] = "ready"
        store.save(run, "resumed")
    elif run["status"] not in ("ready",):
        raise ValueError("Use resume for a previously started run.")
    configured = Limits.model_validate(run["limits"])
    started, prior_elapsed = time.monotonic(), run["elapsed_seconds"]

    def elapsed():
        return prior_elapsed + time.monotonic()-started

    def remaining():
        return max(0.0, configured.total_seconds-elapsed())

    def save(state, event):
        state["elapsed_seconds"] = elapsed()
        store.save(state, event)

    def should_stop(state):
        if store.read(run_id)["stop_requested"]:
            return "stopped"
        if remaining() <= 0:
            return "time_budget_exhausted"
        if state["attempts"] >= configured.max_steps:
            return "step_budget_exhausted"
        return None

    def propose(data):
        state = data["run"]
        stop = should_stop(state)
        if stop:
            state["status"] = stop
            save(state, stop)
            return {"run": state}
        if state["pending"] is not None:
            state["status"] = "calculating"
            return {"run": state}
        if state["llm_calls"] >= configured.max_llm_calls or state["completion_tokens"] >= configured.total_output_tokens:
            state["status"] = "llm_budget_exhausted"
            save(state, state["status"])
            return {"run": state}
        if not state["messages"]:
            state["messages"] = [{"role": "system", "content": SYSTEM+"\nAvailable tools:\n"+json_text(list_tools())},
                                 {"role": "user", "content": json_text({"model": state["model"], "goal": state["goal"]})}]
        if len(json_text(state["messages"])) > 100000:
            state["status"] = "context_budget_exhausted"
            save(state, state["status"])
            return {"run": state}
        state["llm_calls"] += 1  # Charge attempts before sending; a crash does not refund a call.
        state["status"] = "proposing"
        requested_tokens = min(configured.max_output_tokens, configured.total_output_tokens-state["completion_tokens"])
        # Reserve the full possible completion before sending. A timeout, lost
        # response or crash cannot silently refund an unknown token expenditure.
        state["completion_tokens"] += requested_tokens
        save(state, "llm_request")
        try:
            reply = source.complete(state["messages"], timeout=min(configured.llm_seconds, remaining()), max_tokens=requested_tokens)
        except BackendFailure as exc:
            state["status"] = exc.code
            save(state, exc.code)
            return {"run": state}
        state["prompt_tokens"] += reply.get("prompt_tokens", 0)
        if reply.get("completion_tokens") is not None:
            state["completion_tokens"] += reply["completion_tokens"]-requested_tokens
        state["last_response"] = {key: reply.get(key) for key in ("model", "response_id", "prompt_tokens", "completion_tokens")}
        content = reply["content"]
        state["messages"].append({"role": "assistant", "content": content})
        try:
            if len(content) > 50000:
                raise ValueError("Response too long.")
            action = Action.model_validate(load_json(content))
            if action.tool != "finish" and action.tool not in REGISTRY:
                raise ValueError("Unknown tool.")
        except (ValueError, TypeError):
            state["messages"].append({"role": "user", "content": "Invalid action JSON. Return one object with tool, arguments, reason using a registered tool."})
            state["status"] = "ready"
            save(state, "invalid_proposal")
            return {"run": state}
        if action.tool == "finish":
            state["status"] = "agent_stopped"
            state["proposal_for_next_work"] = {"text": action.reason, "status": "unverified_suggestion"}
        else:
            state["pending"] = action.model_dump()
            state["status"] = "calculating"
        save(state, "proposal")
        return {"run": state}

    def calculate(data):
        state = data["run"]
        stop = should_stop(state)
        if stop:
            state["status"] = stop
            save(state, stop)
            return {"run": state}
        action = state["pending"]
        args = dict(action["arguments"])
        fields = REGISTRY[action["tool"]].arguments.model_fields
        if "model" in fields:
            args["model"] = state["model"]
        if "run_id" in fields:
            args["run_id"], args["model_revision"] = run_id, state["model_revision"]
        state["attempts"] += 1
        save(state, "calculation_started")
        seconds_left = remaining()
        if seconds_left <= 0:
            state["status"] = "time_budget_exhausted"
            save(state, state["status"])
            return {"run": state}
        outcome = call_tool(action["tool"], args, timeout_seconds=min(configured.tool_seconds, seconds_left), memory_mb=configured.memory_mb)
        state["history"].append({"attempt": state["attempts"], "tool": action["tool"], "arguments": args,
                                 "reason": action["reason"], "outcome": outcome})
        state["messages"].append({"role": "user", "content": "Calculation result:\n"+json_text(outcome)})
        state["pending"] = None
        state["status"] = "verified" if _has_verified(outcome) else "ready"
        save(state, "calculation_finished")
        return {"run": state}

    graph = StateGraph(GraphState)
    graph.add_node("propose", propose)
    graph.add_node("calculate", calculate)
    graph.add_edge(START, "propose")
    graph.add_conditional_edges("propose", lambda data: "calculate" if data["run"]["status"] == "calculating" else (
        "propose" if data["run"]["status"] == "ready" else END))
    graph.add_conditional_edges("calculate", lambda data: "propose" if data["run"]["status"] == "ready" else END)
    # Each node commits a portable state to SQLite. On resume, rebuild the graph
    # from that state; no pickle or framework-specific checkpoint is required.
    try:
        return graph.compile().invoke({"run": run}, {"recursion_limit": 2*(configured.max_steps+configured.max_llm_calls)+10})["run"]
    except KeyboardInterrupt:
        state = store.read(run_id)
        state["status"] = "interrupted"
        save(state, "interrupted")
        return state
