"""One registry and a bounded worker shared by Python, MCP and the agent."""

import importlib
import multiprocessing as mp
import time
from dataclasses import dataclass
from typing import Annotated

from pydantic import Field, ValidationError

from .expressions import InputError
from .inputs import Expression, StrictModel, pcm_model
from .physics import derive_equations, solve_scalar_ansatz, verify_candidate, verify_scalar


class EquationArguments(StrictModel):
    model: dict = Field(default_factory=pcm_model)


class VerifyArguments(EquationArguments):
    candidate: dict
    run_id: str = "standalone"
    model_revision: Annotated[int, Field(ge=1)] = 1
    removal_gauge: list[list[str]] | None = None
    check_essential: bool = True


class SolveArguments(StrictModel):
    plus: Expression
    minus: Expression
    unknowns: Annotated[list[str], Field(min_length=1, max_length=6)]
    run_id: str = "standalone"
    model_revision: Annotated[int, Field(ge=1)] = 1


class ScalarArguments(EquationArguments):
    plus: Expression
    minus: Expression
    exclude_zeros: list[Expression] | None = None
    run_id: str = "standalone"
    model_revision: Annotated[int, Field(ge=1)] = 1


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    arguments: type[StrictModel]
    handler: object


REGISTRY = {
    "pcm_equations": Tool("pcm_equations", "Derive all PCM EOM by constrained group variation. Omit model to select the documented SU(2) PCM; the full model definition is returned.", EquationArguments, derive_equations),
    "pcm_verify": Tool("pcm_verify", "Check flatness, recovery of all EOM and spectral nonremovability.", VerifyArguments, verify_candidate),
    "pcm_verify_scalar": Tool("pcm_verify_scalar", "Verify L_plus=plus(z)*j_plus and L_minus=minus(z)*j_minus. Missing exclusions are derived from denominators.", ScalarArguments, verify_scalar),
    "pcm_solve_scalar": Tool("pcm_solve_scalar", "Solve 1–6 constant coefficients in a rational scalar current ansatz and verify the candidates.", SolveArguments, solve_scalar_ansatz),
}


def register_tool(tool: Tool):
    """Trusted Python extensions register an importable handler and argument model."""
    if tool.name in REGISTRY:
        raise ValueError(f"Tool already registered: {tool.name}")
    if "<locals>" in tool.handler.__qualname__:
        raise ValueError("Handler must be importable at module scope.")
    REGISTRY[tool.name] = tool


def list_tools():
    return [{"name": t.name, "description": t.description, "input_schema": t.arguments.model_json_schema()}
            for t in REGISTRY.values()]


def _worker(connection, module, qualname, arguments, memory_mb):
    try:
        if memory_mb is not None:
            try:
                import resource
                resource.setrlimit(resource.RLIMIT_AS, (memory_mb*1024**2, memory_mb*1024**2))
            except ImportError:
                connection.send({"status": "unsupported_resource_limit", "reason": "Memory limits require POSIX resource support."})
                return
        handler = importlib.import_module(module)
        for name in qualname.split("."):
            handler = getattr(handler, name)
        connection.send({"status": "completed", "result": handler(**arguments)})
    except InputError as exc:
        connection.send({"status": "invalid_input", "error": exc.as_dict()})
    except MemoryError:
        connection.send({"status": "resource_limit", "reason": "Worker memory limit reached."})
    except Exception as exc:
        # Keep arbitrary exception text out of external results and saved traces.
        connection.send({"status": "internal_error", "exception_type": type(exc).__name__})
    finally:
        connection.close()


def call_tool(name: str, arguments: dict, *, timeout_seconds=30.0, memory_mb=None) -> dict:
    """Execute one registered calculation in a disposable process.

    Timeouts return no physical verdict. Raw Python functions remain available
    for notebooks whose caller supplies its own execution policy.
    """
    if name not in REGISTRY:
        return {"status": "unknown_tool", "name": name}
    if not 0 < timeout_seconds <= 3600:
        raise ValueError("timeout_seconds must be in (0, 3600].")
    if memory_mb is not None and (type(memory_mb) is not int or memory_mb < 128):
        raise ValueError("memory_mb must be an integer of at least 128 or None.")
    tool = REGISTRY[name]
    try:
        validated = tool.arguments.model_validate(arguments).model_dump()
    except ValidationError as exc:
        return {"status": "invalid_input", "error": {"code": "INVALID_STRUCTURE", "message": exc.errors()[0]["msg"]}}
    context = mp.get_context("spawn")
    reader, writer = context.Pipe(duplex=False)
    process = context.Process(target=_worker, args=(writer, tool.handler.__module__, tool.handler.__qualname__, validated, memory_mb))
    started = time.monotonic()
    process.start()
    writer.close()
    try:
        if reader.poll(timeout_seconds):
            try:
                result = reader.recv()
            except EOFError:
                result = {"status": "worker_failed", "reason": "Worker ended without a result."}
        else:
            result = {"status": "timeout", "reason": "Calculation exceeded its wall time; no verdict was assigned."}
    finally:
        if process.is_alive():
            process.terminate()
        process.join(timeout=2)
        if process.is_alive():
            process.kill()
            process.join()
        reader.close()
    result["elapsed_seconds"] = round(time.monotonic()-started, 6)
    return result
