"""Deterministic integration fixture, explicitly not a language model."""

from .storage import json_text, load_json


class DemoSource:
    def complete(self, messages, *, timeout, max_tokens):
        results = [m["content"] for m in messages if m["content"].startswith("Calculation result:\n")]
        if not results:
            action = {"tool": "pcm_verify_scalar", "arguments": {"plus": "1", "minus": "1"},
                      "reason": "Integration fixture: first test the current itself, whose flatness need not encode dynamics."}
        else:
            previous = load_json(results[-1].split("\n", 1)[1])
            if previous["status"] != "completed" or previous["result"].get("checks", {}).get("eom_recovery", {}).get("status") != "failed":
                raise RuntimeError("The fixture expected explicit EOM-recovery failure.")
            action = {"tool": "pcm_solve_scalar", "arguments": {"plus": "a/(1-z)", "minus": "b/(1+z)", "unknowns": ["a", "b"]},
                      "reason": "Integration fixture: after the missing-EOM result, try unequal rational spectral functions and solve their constants."}
        return {"content": json_text(action), "prompt_tokens": 0, "completion_tokens": 0,
                "model": "deterministic-integration-fixture", "response_id": None}
