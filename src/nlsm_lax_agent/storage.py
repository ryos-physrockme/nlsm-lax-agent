"""SQLite run records and portable, model-free rechecks."""

import hashlib
import importlib.metadata
import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path

from . import __version__
from .inputs import validate_model


def json_text(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def load_json(text):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result
    return json.loads(text, object_pairs_hook=unique, parse_constant=lambda x: (_ for _ in ()).throw(ValueError("Nonfinite JSON number")))


def environment_versions():
    versions = {"nlsm-lax-agent": __version__}
    for package in ("sympy", "pydantic", "mcp", "langgraph", "litellm"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            pass
    return versions


class RunStore:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as con:
            con.execute("CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, state TEXT NOT NULL)")
            con.execute("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL, payload TEXT NOT NULL)")
            con.execute("CREATE TABLE IF NOT EXISTS leases (run_id TEXT PRIMARY KEY, pid INTEGER NOT NULL)")

    def connect(self):
        return sqlite3.connect(self.path, timeout=30)

    def create(self, model, goal, limits, backend):
        run_id = uuid.uuid4().hex
        state = {"schema_version": 1, "run_id": run_id, "model_revision": 1,
                 "model": validate_model(model), "goal": goal, "limits": limits,
                 "backend": backend, "versions": environment_versions(),
                 "status": "ready", "attempts": 0, "llm_calls": 0,
                 "prompt_tokens": 0, "completion_tokens": 0, "elapsed_seconds": 0.0,
                 "history": [], "messages": [], "pending": None, "stop_requested": False}
        with self.connect() as con:
            con.execute("INSERT INTO runs VALUES (?, ?)", (run_id, json_text(state)))
        self.save(state, "created")
        return state

    def read(self, run_id):
        with self.connect() as con:
            row = con.execute("SELECT state FROM runs WHERE id=?", (run_id,)).fetchone()
        if row is None:
            raise KeyError("Unknown run ID.")
        return load_json(row[0])

    def save(self, state, event):
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            # Preserve a stop request made concurrently by another process.
            row = con.execute("SELECT state FROM runs WHERE id=?", (state["run_id"],)).fetchone()
            if row and load_json(row[0]).get("stop_requested") and event != "resumed":
                state["stop_requested"] = True
            con.execute("UPDATE runs SET state=? WHERE id=?", (json_text(state), state["run_id"]))
            con.execute("INSERT INTO events(run_id,payload) VALUES (?,?)", (state["run_id"], json_text({"event": event, "state": state})))

    def request_stop(self, run_id):
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT state FROM runs WHERE id=?", (run_id,)).fetchone()
            if row is None:
                raise KeyError("Unknown run ID.")
            state = load_json(row[0])
            state["stop_requested"] = True
            con.execute("UPDATE runs SET state=? WHERE id=?", (json_text(state), run_id))
            con.execute("INSERT INTO events(run_id,payload) VALUES (?,?)", (run_id, json_text({"event": "stop_requested", "state": state})))

    @contextmanager
    def claim(self, run_id):
        """Only one agent writer per run, on a local, single-host database."""
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            previous = con.execute("SELECT pid FROM leases WHERE run_id=?", (run_id,)).fetchone()
            if previous:
                try:
                    os.kill(previous[0], 0)
                except ProcessLookupError:
                    con.execute("DELETE FROM leases WHERE run_id=?", (run_id,))
                else:
                    raise ValueError("This run is already being processed by another agent.")
            con.execute("INSERT INTO leases VALUES (?, ?)", (run_id, os.getpid()))
        try:
            yield
        finally:
            with self.connect() as con:
                con.execute("DELETE FROM leases WHERE run_id=? AND pid=?", (run_id, os.getpid()))

    def export(self, run_id):
        with self.connect() as con:
            events = [load_json(row[0]) for row in con.execute("SELECT payload FROM events WHERE run_id=? ORDER BY id", (run_id,))]
        payload = {"schema_version": 1, "state": self.read(run_id), "events": events}
        return {"payload": payload, "sha256": hashlib.sha256(json_text(payload).encode()).hexdigest()}


def recheck(bundle):
    """Recompute recorded tool results; a digest is integrity checking, not authentication."""
    from .tools import call_tool
    payload = bundle["payload"]
    if hashlib.sha256(json_text(payload).encode()).hexdigest() != bundle["sha256"]:
        raise ValueError("Export digest mismatch.")
    state = payload["state"]
    if state["schema_version"] != 1:
        raise ValueError("Unsupported export version.")
    validate_model(state["model"])
    comparisons = []
    for entry in state["history"]:
        if entry["outcome"]["status"] != "completed":
            comparisons.append({"attempt": entry["attempt"], "status": "not_rechecked", "reason": "No completed calculation."})
            continue
        current = call_tool(entry["tool"], entry["arguments"], timeout_seconds=state["limits"]["tool_seconds"])
        same = current["status"] == "completed" and current["result"] == entry["outcome"]["result"]
        comparisons.append({"attempt": entry["attempt"], "status": "match" if same else "mismatch"})
    return {"status": "match" if comparisons and all(x["status"] == "match" for x in comparisons) else "incomplete_or_mismatch",
            "comparisons": comparisons, "recorded_versions": state["versions"], "current_versions": environment_versions()}
