"""Public formula helpers and validation of the common calculation input."""

from copy import deepcopy
from typing import Annotated, Literal

import sympy as s
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .expressions import InputError, read_expression, spectral_domain


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


Expression = Annotated[str, Field(min_length=1, max_length=2048)]
Row = Annotated[list[Expression], Field(min_length=3, max_length=3)]
Matrix = Annotated[list[Row], Field(min_length=3, max_length=3)]


class Term(StrictModel):
    current: Literal["j_plus", "j_minus"]
    matrix: Matrix


class Components(StrictModel):
    plus: Annotated[list[Term], Field(max_length=2)]
    minus: Annotated[list[Term], Field(max_length=2)]


class Spectrum(StrictModel):
    name: Literal["z"]
    base: Literal["complex_plane"]
    exclude_zeros: Annotated[list[Expression], Field(max_length=16)]


class ModelReference(StrictModel):
    run_id: Annotated[str, Field(min_length=1, max_length=128)]
    model_revision: Annotated[int, Field(ge=1)]


class GaugeConditions(StrictModel):
    group: Literal["SL2C"]
    dependence: Literal["local_finite_jet"]
    regularity: Literal["smooth_fields_holomorphic_z"]
    scope: Literal["generic_local"]


class Candidate(StrictModel):
    schema_version: Literal[1]
    model_ref: ModelReference
    representation: Literal["su2_current_linear_v1"]
    spectral_parameter: Spectrum
    components: Components
    gauge_equivalence: GaugeConditions


def pcm_model(action_prefactor="-1/(2*kappa**2)") -> dict:
    """Specify S = action_prefactor * integral tr(j_plus*j_minus), g in SU(2)."""
    return {
        "schema_version": 1, "model_type": "su2_pcm", "conventions": "su2_left_current_v1",
        "field": {"name": "g", "target": "SU2"},
        "coupling": {"name": "kappa", "domain": "positive_real"},
        "action": {"measure": ["x_plus", "x_minus"], "prefactor": str(action_prefactor),
                   "pairing": "trace_fundamental", "currents": ["j_plus", "j_minus"]},
        "domain": {"spacetime": "contractible_lorentzian_patch", "field_regularity": "smooth",
                   "boundary_conditions": "none", "variation": "compact_support"},
    }


def scalar_candidate(plus, minus, *, exclude_zeros=None, run_id="standalone", model_revision=1):
    """Construct L_plus=plus(z)*j_plus, L_minus=minus(z)*j_minus.

    Omitted exclusions are derived from the original denominators, including
    factors which cancel. Explicit exclusions are checked by the verifier.
    """
    plus, minus = str(plus), str(minus)
    if exclude_zeros is None:
        conditions = []
        for expr in (plus, minus):
            parsed = read_expression(expr)
            conditions.extend(parsed.nonzero)
            conditions.append(s.denom(parsed.value))
        exclude_zeros = list(dict.fromkeys(str(c) for c in conditions if s.Symbol("z") in c.free_symbols))
    def term(current, value):
        return [{"current": current, "matrix": [[value if i == j else "0" for j in range(3)] for i in range(3)]}]
    return {
        "schema_version": 1, "model_ref": {"run_id": run_id, "model_revision": model_revision},
        "representation": "su2_current_linear_v1",
        "spectral_parameter": {"name": "z", "base": "complex_plane", "exclude_zeros": exclude_zeros},
        "components": {"plus": term("j_plus", plus), "minus": term("j_minus", minus)},
        "gauge_equivalence": {"group": "SL2C", "dependence": "local_finite_jet",
                              "regularity": "smooth_fields_holomorphic_z", "scope": "generic_local"},
    }


def validate_model(data):
    if not isinstance(data, dict):
        raise InputError("INVALID_STRUCTURE", "Expected a model object.")
    expected = pcm_model()
    try:
        supplied = deepcopy(data)
        prefactor = supplied["action"]["prefactor"]
        supplied["action"]["prefactor"] = expected["action"]["prefactor"]
    except (KeyError, TypeError) as exc:
        raise InputError("INVALID_STRUCTURE", "Missing model action.") from exc
    if type(data.get("schema_version")) is not int or supplied != expected:
        raise InputError("UNSUPPORTED_SPECIFICATION", "This backend accepts only the documented SU(2) PCM conventions.")
    parsed = read_expression(prefactor, ("kappa",))
    k = s.Symbol("kappa")
    if s.cancel(parsed.value + 1/(2*k**2)) != 0:
        raise InputError("UNSUPPORTED_ACTION", "Expected the PCM action coefficient -1/(2*kappa**2).")
    for condition in parsed.nonzero:
        p = s.Poly(condition, k, domain=s.QQ)
        if p.count_roots(0, s.oo) > (1 if p.eval(0) == 0 else 0):
            raise InputError("UNDECLARED_SINGULARITY", "Action is undefined for some positive kappa.")
    result = deepcopy(data)
    result["action"]["prefactor"] = str(parsed.value)
    return result


def validate_candidate(data, registered_model):
    try:
        candidate = Candidate.model_validate(data)
    except ValidationError as exc:
        error = exc.errors()[0]
        raise InputError("INVALID_STRUCTURE", error["msg"], "/" + "/".join(map(str, error["loc"]))) from exc
    if type(data["schema_version"]) is not int:
        raise InputError("INVALID_STRUCTURE", "schema_version must be an integer.")
    if not isinstance(registered_model, dict) or candidate.model_ref.model_dump() != {
        "run_id": registered_model.get("run_id"), "model_revision": registered_model.get("model_revision")
    }:
        raise InputError("MODEL_REFERENCE_MISMATCH", "Candidate refers to another model or revision.")
    validate_model(registered_model["definition"])
    result = candidate.model_dump()
    expressions = []
    for component in ("plus", "minus"):
        terms = result["components"][component]
        if len({term["current"] for term in terms}) != len(terms):
            raise InputError("INVALID_STRUCTURE", "Repeated current in a connection component.")
        for ti, term in enumerate(terms):
            for i, row in enumerate(term["matrix"]):
                for j, value in enumerate(row):
                    try:
                        parsed = read_expression(value)
                    except InputError as exc:
                        exc.path = f"/components/{component}/{ti}/matrix/{i}/{j}"
                        raise
                    expressions.append(parsed)
                    row[j] = str(parsed.value)
        terms.sort(key=lambda term: ("j_plus", "j_minus").index(term["current"]))
    result["spectral_parameter"]["exclude_zeros"] = spectral_domain(
        result["spectral_parameter"]["exclude_zeros"], expressions)
    return result


def _normalize(fn, *args):
    try:
        return {"status": "accepted", "value": fn(*args), "error": None}
    except InputError as exc:
        return {"status": "rejected", "value": None, "error": exc.as_dict()}


def normalize_model(data):
    return _normalize(validate_model, data)


def normalize_candidate(data, registered_model):
    return _normalize(validate_candidate, data, registered_model)
