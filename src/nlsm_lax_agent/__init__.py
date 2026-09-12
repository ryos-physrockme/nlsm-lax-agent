"""Physics functions do not import an LLM SDK or an agent framework."""

__version__ = "0.1.0"

from .inputs import pcm_model, scalar_candidate
from .physics import derive_equations, solve_scalar_ansatz, verify_candidate

__all__ = ["pcm_model", "scalar_candidate", "derive_equations",
           "solve_scalar_ansatz", "verify_candidate"]
