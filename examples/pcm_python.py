"""Run with python examples/pcm_python.py after installing the package."""
import json

from nlsm_lax_agent import pcm_model, scalar_candidate, derive_equations, verify_candidate, solve_scalar_ansatz


if __name__ == "__main__":
    model = pcm_model("-1/(2*kappa**2)")
    print(json.dumps(derive_equations(model), indent=2))
    candidate = scalar_candidate("1/(1-z)", "1/(1+z)")
    print(json.dumps(verify_candidate(candidate, model), indent=2))
    print(json.dumps(solve_scalar_ansatz("a/(1-z)", "b/(1+z)", ["a", "b"]), indent=2))
