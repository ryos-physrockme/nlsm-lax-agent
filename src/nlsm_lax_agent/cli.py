"""Small CLI for calculation, configured agents, and portable rechecks."""

import argparse
import json
import sys
import tomllib
from pathlib import Path

from .inputs import pcm_model, validate_model
from .storage import RunStore, load_json, recheck
from .tools import call_tool, list_tools


def emit(value, output=None):
    text = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+"\n"
    if output:
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="nlsm-lax")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("tools")
    calculate = sub.add_parser("calculate")
    calculate.add_argument("tool")
    calculate.add_argument("input", help="JSON file containing the calculation arguments")
    calculate.add_argument("--tool-seconds", type=float, default=30.0)
    for name in ("agent", "demo"):
        p = sub.add_parser(name)
        p.add_argument("--database", default="runs/pcm.sqlite")
        p.add_argument("--output", help="Write the portable run export")
        if name == "agent":
            p.add_argument("config", help="TOML with model, research goal, LLM profile and limits")
            p.add_argument("--resume", metavar="RUN_ID")
            p.add_argument("--direction", help="Record a researcher's new direction on resume")
    for name in ("show", "stop", "export"):
        p = sub.add_parser(name)
        p.add_argument("run_id")
        p.add_argument("--database", default="runs/pcm.sqlite")
        if name == "export":
            p.add_argument("--output", required=True)
    p = sub.add_parser("recheck")
    p.add_argument("input")
    args = parser.parse_args(argv)
    if args.command == "tools":
        emit(list_tools())
    elif args.command == "calculate":
        result = call_tool(args.tool, load_json(Path(args.input).read_text()), timeout_seconds=args.tool_seconds)
        emit(result)
        return 0 if result["status"] == "completed" else 1
    elif args.command == "recheck":
        result = recheck(load_json(Path(args.input).read_text()))
        emit(result)
        return 0 if result["status"] == "match" else 1
    else:
        store = RunStore(args.database)
        if args.command == "show":
            emit(store.read(args.run_id))
        elif args.command == "stop":
            store.request_stop(args.run_id)
            emit({"run_id": args.run_id, "status": "stop_requested"})
        elif args.command == "export":
            emit(store.export(args.run_id), args.output)
        else:
            from .agent import BackendConfig, Limits, LiteLLMSource, run_agent
            if args.command == "demo":
                from .demo import DemoSource
                source, limits = DemoSource(), Limits()
                run = store.create(pcm_model(), "Demonstrate rejection, ansatz revision and exact verification.",
                                   limits.model_dump(), {"kind": "deterministic_fixture", "is_llm": False})
                result = run_agent(store, run["run_id"], source)
            else:
                config = tomllib.loads(Path(args.config).read_text())
                backend = BackendConfig.model_validate(config["llm"])
                limits = Limits.model_validate(config.get("limits", {}))
                source = LiteLLMSource(backend)
                if args.resume:
                    run = store.read(args.resume)
                    if run["backend"] != backend.model_dump():
                        raise ValueError("Resume with the recorded backend; start another run for a backend comparison.")
                    if run["model"] != validate_model(pcm_model(config["model"]["action_prefactor"])) or run["goal"] != config["goal"]:
                        raise ValueError("Resume with the recorded model and goal; use --direction for steering.")
                    result = run_agent(store, args.resume, source, resume=True, direction=args.direction, limits=limits.model_dump())
                else:
                    if args.direction:
                        parser.error("--direction requires --resume")
                    run = store.create(pcm_model(config["model"]["action_prefactor"]), config["goal"], limits.model_dump(), backend.model_dump())
                    print(f"Started run {run['run_id']} (database: {args.database})", file=sys.stderr, flush=True)
                    result = run_agent(store, run["run_id"], source)
            if args.output:
                emit(store.export(result["run_id"]), args.output)
            emit({"run_id": result["run_id"], "status": result["status"], "attempts": result["attempts"],
                  "llm_calls": result["llm_calls"], "backend": result["backend"], "database": args.database})
            return 0 if result["status"] == "verified" else 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)
