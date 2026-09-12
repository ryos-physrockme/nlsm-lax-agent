from copy import deepcopy

import pytest
import sympy as s

from nlsm_lax_agent import derive_equations, pcm_model, scalar_candidate, solve_scalar_ansatz, verify_candidate
from nlsm_lax_agent.expressions import InputError, read_expression
from nlsm_lax_agent.inputs import normalize_candidate, normalize_model
from nlsm_lax_agent.physics import _spectral_span


def test_pcm_euler_equations_and_full_curvature_identity():
    equations = derive_equations()
    assert equations["eom"] == [f"dminus_jp{i} + dplus_jm{i}" for i in range(1, 4)]
    k = s.Symbol("kappa")
    assert read_expression(equations["nonzero_common_factor"], ("kappa",)).value == -1/(4*k**2)
    result = verify_candidate(scalar_candidate("1/(1-z)", "1/(1+z)"))
    assert result["status"] == "verified"
    z = s.Symbol("z")
    assert s.cancel(read_expression(result["decomposition"]["eom_coefficient"][0][0]).value + z/(1-z**2)) == 0
    assert result["decomposition"]["remainder"] == ["0"]*3
    assert result["checks"]["eom_recovery"]["rank"] == 3
    essential = result["checks"]["spectral_nonremovability"]
    assert s.cancel(read_expression(essential["trace_gram"][0][0]).value + z**2/(2*(1-z**2)**2)) == 0


@pytest.mark.parametrize("plus,minus", [("0", "0"), ("1", "1")])
def test_flat_connections_do_not_pass_without_dynamics_or_parameter(plus, minus):
    result = verify_candidate(scalar_candidate(plus, minus))
    assert result["status"] == "rejected"
    assert result["checks"]["on_shell_flatness"]["status"] == "passed"
    assert result["checks"]["eom_recovery"]["status"] == "failed"
    assert result["checks"]["spectral_nonremovability"]["status"] == "failed"


def test_wrong_sign_rejected_and_reparameterized_family_passes():
    assert verify_candidate(scalar_candidate("1/(1-z)", "1/(1-z)"))["checks"]["on_shell_flatness"]["status"] == "failed"
    assert verify_candidate(scalar_candidate("1/(1-z**2)", "1/(1+z**2)"))["status"] == "verified"


def gauge_conjugate(plus, minus):
    candidate = scalar_candidate(plus, minus)
    z = s.Symbol("z")
    a, b = (z**2+z**-2)/2, (z**2-z**-2)/2
    adjoint = s.Matrix([[a, -s.I*b, 0], [s.I*b, a, 0], [0, 0, 1]])
    for direction, factor in (("plus", plus), ("minus", minus)):
        m = adjoint*read_expression(factor).value
        candidate["components"][direction][0]["matrix"] = [[str(v) for v in row] for row in m.tolist()]
    candidate["spectral_parameter"]["exclude_zeros"].append("z")
    return candidate


def test_removable_gauge_parameter_has_a_checked_inverse():
    fake = gauge_conjugate("1", "1")
    result = verify_candidate(fake, removal_gauge=[["1/z", "0"], ["0", "z"]])
    assert result["checks"]["on_shell_flatness"]["status"] == "passed"
    assert result["checks"]["spectral_nonremovability"]["status"] == "failed"
    with pytest.raises(InputError, match="does not remove"):
        verify_candidate(fake, removal_gauge=[["1", "0"], ["0", "1"]])


def test_local_gauge_change_does_not_destroy_nonremovability_certificate():
    result = verify_candidate(gauge_conjugate("1/(1-z)", "1/(1+z)"))
    assert result["status"] == "verified"


def test_inconclusive_or_skipped_check_cannot_become_verified():
    result = verify_candidate(scalar_candidate("1/(1-z)", "1/(1+z)"), check_essential=False)
    assert result["status"] == "unverified"
    assert result["checks"]["spectral_nonremovability"]["status"] == "undetermined"
    result = verify_candidate(gauge_conjugate("1", "1"))
    assert result["checks"]["spectral_nonremovability"]["status"] == "undetermined"


def test_spectral_span_uses_the_family_not_a_single_point():
    z = s.Symbol("z")
    Q = s.Matrix([[1, z, z**2], [0, 0, 0], [0, 0, 0]])
    assert Q.rank() == 1
    assert _spectral_span(Q)["rank"] == 3


def test_coefficient_solve_finds_and_verifies_nontrivial_branch():
    result = solve_scalar_ansatz("a/(1-z)", "b/(1+z)", ["a", "b"])
    good = [c for c in result["candidates"] if c["verification"]["status"] == "verified"]
    assert [c["coefficients"] for c in good] == [{"a": "1", "b": "1"}]
    assert any(c["verification"]["status"] == "rejected" for c in result["candidates"])


@pytest.mark.parametrize("expression", ["__import__('os')", "z.real", "z[0]", "1.0", "True", "0x10", "z**z", "z^2"])
def test_expression_reader_rejects_unsupported_input(expression):
    with pytest.raises(InputError):
        read_expression(expression)


def test_cancelled_poles_and_domain_self_reference_are_preserved():
    candidate = scalar_candidate("(z-2)/(z-2)", "1", exclude_zeros=[])
    with pytest.raises(InputError, match="Exclude the zeros"):
        verify_candidate(candidate)
    candidate["spectral_parameter"]["exclude_zeros"] = ["z-2"]
    assert verify_candidate(candidate)["status"] == "rejected"
    candidate = scalar_candidate("1", "1", exclude_zeros=["(z-2)/(z-2)"])
    with pytest.raises(InputError):
        verify_candidate(candidate)


def test_action_positive_domain_and_model_revision_are_checked():
    good = pcm_model("-(kappa+1)/(2*kappa**2*(kappa+1))")
    assert normalize_model(good)["status"] == "accepted"
    bad = pcm_model("-(kappa-1)/(2*kappa**2*(kappa-1))")
    assert normalize_model(bad)["status"] == "rejected"
    model = pcm_model()
    bad = deepcopy(model)
    bad["schema_version"] = True
    assert normalize_model(bad)["status"] == "rejected"
    record = {"run_id": "different", "model_revision": 1, "definition": model}
    assert normalize_candidate(scalar_candidate("1", "1"), record)["error"]["code"] == "MODEL_REFERENCE_MISMATCH"
