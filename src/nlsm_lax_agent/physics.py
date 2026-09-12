"""Exact PCM calculations; no language model participates in a verdict."""

import re

import sympy as s

from .expressions import InputError, read_expression, spectral_domain
from .inputs import pcm_model, scalar_candidate, validate_candidate, validate_model

z = s.Symbol("z")
T = [-s.I*s.Matrix([[0, 1], [1, 0]])/2,
     -s.I*s.Matrix([[0, -s.I], [s.I, 0]])/2,
     -s.I*s.diag(1, -1)/2]


def matrix_strings(matrix):
    return [[str(s.cancel(x)) for x in row] for row in matrix.tolist()]


def vector_strings(vector):
    return [str(s.cancel(x)) for x in vector]


def matrices(candidate):
    result = {}
    for direction in ("plus", "minus"):
        for current in ("j_plus", "j_minus"):
            term = next((t for t in candidate["components"][direction] if t["current"] == current), None)
            result[direction, current] = s.zeros(3) if term is None else s.Matrix([
                [read_expression(value).value for value in row] for row in term["matrix"]])
    return result


def derive_equations(model=None):
    """Vary g by delta(g)=g*epsilon and integrate by parts, retaining all 3 EOM."""
    model = validate_model(pcm_model() if model is None else model)
    p, q, a, b, eps, dp, dm = [s.Matrix(s.symbols(f"{prefix}1:4"))
                              for prefix in ("jp", "jm", "dplus_jm", "dminus_jp", "eps", "dplus_eps", "dminus_eps")]
    prefactor = read_expression(model["action"]["prefactor"], ("kappa",)).value
    variation = s.expand(-prefactor*((dp+p.cross(eps)).dot(q) + p.dot(dm+q.cross(eps)))/2)
    euler = []
    for i in range(3):
        euler.append(s.cancel(s.diff(variation, eps[i]) - sum(
            s.diff(variation, dp[i], q[j])*a[j] + s.diff(variation, dm[i], p[j])*b[j] for j in range(3))))
    return {"model": model, "variation_before_integration_by_parts": str(variation),
            "euler_coefficients": vector_strings(euler), "nonzero_common_factor": str(prefactor/2),
            "eom": vector_strings(s.Matrix(euler)/(prefactor/2)),
            "maurer_cartan": vector_strings(a-b+p.cross(q)),
            "variables": {"jp": "components of g^-1 partial_plus g", "jm": "components of g^-1 partial_minus g",
                          "dplus_jm": "partial_plus j_minus", "dminus_jp": "partial_minus j_plus"}}


def _spectral_span(Q):
    denominator = s.lcm([s.denom(s.cancel(v)) for v in Q])
    polynomial = [[s.Poly(s.cancel(Q[i, j]*denominator), z, extension=s.I) for j in range(3)] for i in range(3)]
    degree = max((p.degree() for row in polynomial for p in row if not p.is_zero), default=0)
    rows = [[polynomial[i][j].nth(k) for j in range(3)] for i in range(3) for k in range(int(degree)+1)]
    stacked = s.Matrix(rows)
    return {"denominator": str(denominator), "coefficient_rows": matrix_strings(stacked),
            "rank": stacked.rank(), "unrecovered_directions": [vector_strings(v) for v in stacked.nullspace()]}


def _removal_witness(ms, witness, exclusions):
    if not isinstance(witness, list) or len(witness) != 2 or any(not isinstance(r, list) or len(r) != 2 for r in witness):
        raise InputError("INVALID_STRUCTURE", "The removal gauge must be a 2 by 2 matrix.")
    parsed = [read_expression(x) for row in witness for x in row]
    spectral_domain(exclusions, parsed)
    h = s.Matrix(2, 2, [p.value for p in parsed])
    if s.cancel(h.det()-1) != 0:
        raise InputError("INVALID_GAUGE_WITNESS", "The gauge must have determinant one.")
    transformed = []
    for matrix in ms.values():
        for j in range(3):
            coefficient = sum((matrix[i, j]*T[i] for i in range(3)), s.zeros(2))
            transformed.append((h*coefficient*h.inv()).applyfunc(s.cancel))
    if any(s.cancel(s.diff(v, z)) != 0 for m in transformed for v in m):
        raise InputError("INVALID_GAUGE_WITNESS", "The supplied gauge does not remove the parameter.")
    return {"h": matrix_strings(h), "transformed_current_coefficients": [matrix_strings(m) for m in transformed],
            "reason": "h depends only on z; partial_plus h = partial_minus h = 0."}


def verify_candidate(candidate, model=None, *, run_id="standalone", model_revision=1,
                     removal_gauge=None, check_essential=True):
    model = validate_model(pcm_model() if model is None else model)
    candidate = validate_candidate(candidate, {"run_id": run_id, "model_revision": model_revision, "definition": model})
    ms = matrices(candidate)
    P, B, C, D = (ms["plus", "j_plus"], ms["plus", "j_minus"], ms["minus", "j_plus"], ms["minus", "j_minus"])
    p, q, a, b, u, v = [s.Matrix(s.symbols(f"{prefix}1:4")) for prefix in
                        ("jp", "jm", "dplus_jm", "dminus_jp", "dplus_jp", "dminus_jm")]
    E, M = a+b, a-b+p.cross(q)
    Q, R = (D-P)/2, (D+P)/2
    F = C*u+D*a-P*b-B*v+(P*p+B*q).cross(C*p+D*q)
    residual = (F-Q*E-R*M).applyfunc(s.cancel)
    flat = all(value == 0 for value in residual)
    checks = {"on_shell_flatness": {"status": "passed" if flat else "failed",
                                    "residual": vector_strings(residual)},
              "eom_recovery": {"status": "not_run"}, "spectral_nonremovability": {"status": "not_run"}}
    if flat:
        span = _spectral_span(Q)
        checks["eom_recovery"] = {"status": "passed" if span["rank"] == 3 else "failed", **span}
    essential = checks["spectral_nonremovability"]
    if not check_essential:
        essential.update(status="undetermined", reason="Nonremovability check was explicitly disabled.")
    elif removal_gauge is not None:
        witness = _removal_witness(ms, removal_gauge, candidate["spectral_parameter"]["exclude_zeros"])
        essential.update(status="failed", method="explicit_gauge", witness=witness)
    elif all(s.diff(value, z) == 0 for matrix in ms.values() for value in matrix):
        essential.update(status="failed", method="identity_gauge", witness={"h": [["1", "0"], ["0", "1"]]})
    elif flat:
        # For a normal PCM equation in coordinates X, characteristic matrices
        # are 2*sum_a (Q e)^a_i T_a. The left-invariant frame e(X) is invertible
        # and independent of z. A nonconstant Q^T Q therefore implies a
        # nonconstant conjugation invariant of the characteristic elements.
        gram = (-Q.T*Q/2).applyfunc(s.cancel)
        derivative = gram.diff(z).applyfunc(s.cancel)
        varying = next(((i, j) for i in range(3) for j in range(3) if derivative[i, j] != 0), None)
        essential.update(status="passed" if varying else "undetermined",
                         method="characteristic_trace_invariant", trace_gram=matrix_strings(gram),
                         derivative=matrix_strings(derivative), varying_entry=list(varying) if varying else None,
                         scope="All smooth finite-jet local SL(2,C) gauges holomorphic in z on generic open sets.",
                         reference="https://arxiv.org/abs/0804.2031",
                         reason="A nonconstant invariant obstructs removal; a constant invariant is inconclusive.")
    status = "verified" if all(x["status"] == "passed" for x in checks.values()) else (
        "rejected" if any(x["status"] == "failed" for x in checks.values()) else "unverified")
    return {"schema_version": 1, "status": status, "model": model, "candidate": candidate,
            "checks": checks, "curvature": [str(value) for value in F],
            "decomposition": {"eom_coefficient": matrix_strings(Q), "identity_coefficient": matrix_strings(R),
                              "remainder": vector_strings(residual)},
            "conclusion_scope": "This candidate on the declared domain; no assertion of Liouville integrability or model nonintegrability."}


def verify_scalar(plus, minus, model=None, *, exclude_zeros=None, run_id="standalone", model_revision=1):
    candidate = scalar_candidate(plus, minus, exclude_zeros=exclude_zeros, run_id=run_id, model_revision=model_revision)
    return verify_candidate(candidate, model, run_id=run_id, model_revision=model_revision)


def solve_scalar_ansatz(plus: str, minus: str, unknowns: list[str], *, run_id="standalone", model_revision=1):
    """Solve constant coefficients in L_+=a(z)j_+, L_-=b(z)j_-.

    Search is deliberately bounded. Every returned rational candidate is
    independently verified. Denominator-zero branches are rejected.
    """
    if not 1 <= len(unknowns) <= 6 or len(set(unknowns)) != len(unknowns) or any(
        not re.fullmatch(r"[a-h][0-9]?", name) for name in unknowns
    ):
        raise InputError("UNSUPPORTED_ANSATZ", "Use 1–6 distinct coefficient names a..h with an optional digit.")
    names = ("z", "I", *unknowns)
    ap, bp = read_expression(plus, names), read_expression(minus, names)
    a, b = ap.value, bp.value
    obstruction = s.cancel(a*b-(a+b)/2)
    numerator = s.fraction(obstruction)[0]
    equations = s.Poly(numerator, z).all_coeffs()
    variables = [s.Symbol(name) for name in unknowns]
    try:
        solutions = s.solve(equations, variables, dict=True)
    except NotImplementedError:
        return {"ansatz": {"plus": plus, "minus": minus, "unknowns": unknowns},
                "coefficient_equations": [str(e) for e in equations], "candidates": [],
                "unresolved_branches": [], "status": "solver_incomplete",
                "conclusion_scope": "The coefficient solver did not finish this ansatz; no nonexistence claim is made."}
    candidates, unresolved = [], []
    for solution in solutions:
        ae, be = s.cancel(a.subs(solution)), s.cancel(b.subs(solution))
        conditions = [s.cancel(c.subs(solution)) for c in ap.nonzero+bp.nonzero]
        if any(c == 0 or c.has(s.zoo, s.nan) for c in conditions) or ae.has(s.zoo, s.nan) or be.has(s.zoo, s.nan):
            continue
        if (ae.free_symbols | be.free_symbols | set().union(*(c.free_symbols for c in conditions))) - {z}:
            unresolved.append({str(k): str(v) for k, v in solution.items()})
            continue
        try:
            candidate = scalar_candidate(str(ae), str(be), run_id=run_id, model_revision=model_revision)
        except InputError as exc:
            unresolved.append({"coefficients": {str(k): str(v) for k, v in solution.items()},
                               "reason": "Solver branch is outside the supported rational coefficient domain.", "code": exc.code})
            continue
        candidate["spectral_parameter"]["exclude_zeros"].extend(str(c) for c in conditions if z in c.free_symbols)
        result = verify_candidate(candidate, run_id=run_id, model_revision=model_revision)
        candidates.append({"coefficients": {str(k): str(v) for k, v in solution.items()}, "verification": result})
    # SymPy solve returning [] is not a completeness certificate.
    return {"ansatz": {"plus": plus, "minus": minus, "unknowns": unknowns},
            "coefficient_equations": [str(e) for e in equations], "candidates": candidates,
            "unresolved_branches": unresolved,
            "status": "candidates_found" if candidates else "no_candidate_returned",
            "conclusion_scope": "Only the supplied scalar rational ansatz was attempted. An empty solve result is not a No-Go proof."}
