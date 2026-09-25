from unittest.mock import patch

from agent import floor_heating_sizing as sizing_module
from agent import ufh_engineering_kernel as kernel
from agent.ufh_auto_retry import assess_with_automatic_split_retry
from agent.ufh_candidate_adapter import (
    CommonCircuitInputs,
    UFHEngineeringIntegrationInputs,
)
from agent.ufh_engineering_models import Status
from tests.test_floor_heating_sizing import sizing_request
from tests.test_ufh_candidate_adapter import engineering_inputs
from tests.test_ufh_engineering_kernel import valve


def requested(width, height, count, **kwargs):
    request = sizing_request(width, height, **kwargs)
    coverage = request.coverage_request.model_copy(
        update={"requested_circuit_count": count}
    )
    return request.model_copy(update={"coverage_request": coverage})


def pressure_attempt_fixture(count=2, *, sigma=1.5, **kwargs):
    return requested(9000, 3500, count), engineering_inputs(sigma=sigma, **kwargs)


def test_initially_accepted_finishes_after_one_attempt():
    result = assess_with_automatic_split_retry(
        requested(4000, 3000, 1), engineering_inputs()
    )
    assert result.status == "ACCEPTED_INITIAL"
    assert len(result.attempts) == 1
    assert result.attempts[0].actual_circuit_count == 1
    assert result.final_accepted_candidate.engineering.engineering_status == Status.ACCEPTED


def test_hydraulic_split_retries_two_to_three_and_recalculates_every_circuit():
    request, inputs = pressure_attempt_fixture()
    with patch.object(
        sizing_module,
        "solve_floor_heating_coverage",
        wraps=sizing_module.solve_floor_heating_coverage,
    ) as routing, patch.object(kernel, "solve_thermal", wraps=kernel.solve_thermal) as thermal, patch.object(
        kernel, "design_mass_flow", wraps=kernel.design_mass_flow
    ) as flow, patch.object(kernel, "pipe_hydraulics", wraps=kernel.pipe_hydraulics) as hydraulics, patch.object(
        kernel, "circuit_pressure", wraps=kernel.circuit_pressure
    ) as pressure, patch.object(kernel, "balance_circuits", wraps=kernel.balance_circuits) as balance:
        result = assess_with_automatic_split_retry(request, inputs)

    assert result.status == "ACCEPTED_AFTER_RETRY"
    assert [attempt.requested_circuit_count for attempt in result.attempts] == [2, 3]
    initial, retry = result.attempts
    assert [initial.actual_circuit_count, retry.actual_circuit_count] == [2, 3]
    assert initial.engineering_status == Status.REJECTED_CIRCUIT_PRESSURE
    assert initial.retry_reason is None
    assert retry.retry_reason == "EN_CIRCUIT_PRESSURE_LIMIT_EXCEEDED"
    assert retry.engineering_status == Status.ACCEPTED
    assert retry.circuit_lengths_mm == (40100, 40100, 40100)
    assert initial.circuit_lengths_mm == (52100, 52100)
    assert initial.circuit_ids != retry.circuit_ids
    assert initial.circuit_served_areas_m2 != retry.circuit_served_areas_m2
    assert initial.circuit_allocated_heat_w != retry.circuit_allocated_heat_w
    assert initial.circuit_flows_kg_h != retry.circuit_flows_kg_h
    assert initial.circuit_pressures_pa != retry.circuit_pressures_pa
    assert all(p > 35000 for p in initial.circuit_pressures_pa)
    assert all(p < 35000 for p in retry.circuit_pressures_pa)
    assert not any("LEGACY_MINIMUM_CIRCUIT_LENGTH_BLOCKED_SPLIT" in item for item in result.diagnostics)
    assert routing.call_count == 2
    assert thermal.call_count == 5
    assert flow.call_count == 5
    assert hydraulics.call_count == 5
    assert pressure.call_count == 5
    assert balance.call_count == 2

    final = result.final_accepted_candidate
    assert final is not None
    assert final.engineering.circuits[0].candidate.served_area_m2 == retry.circuit_served_areas_m2[0]
    assert final.engineering.circuits[0].mass_flow_kg_h == retry.circuit_flows_kg_h[0]


def test_44_1m_pressure_failure_preserves_root_and_legacy_blocker():
    result = assess_with_automatic_split_retry(
        requested(4000, 3000, 1), engineering_inputs(sigma=0.5)
    )
    assert result.status == "FAILED_NO_ENGINEERING_FEASIBLE_CANDIDATE"
    assert [a.actual_circuit_count for a in result.attempts] == [1, 0]
    assert result.attempts[0].circuit_lengths_mm == (44100,)
    assert result.attempts[0].engineering_status == Status.REJECTED_CIRCUIT_PRESSURE
    assert result.attempts[0].retry_reason is None
    assert result.attempts[1].retry_reason == "EN_CIRCUIT_PRESSURE_LIMIT_EXCEEDED"
    assert result.attempts[1].requested_circuit_count == 2
    assert result.attempts[1].routing_status == "impossible"
    assert "REQUESTED_CIRCUIT_COUNT_NOT_FEASIBLE" in result.diagnostics
    assert any("LEGACY_MINIMUM_CIRCUIT_LENGTH_BLOCKED_SPLIT" in item for item in result.diagnostics)
    assert any("EN_CIRCUIT_PRESSURE_LIMIT_EXCEEDED" in item for item in result.diagnostics)
    assert result.final_accepted_candidate is None


def test_surface_failure_does_not_retry():
    result = assess_with_automatic_split_retry(
        requested(4000, 3000, 1), engineering_inputs(surface=40.0)
    )
    assert result.status == "FAILED_NO_ENGINEERING_FEASIBLE_CANDIDATE"
    assert len(result.attempts) == 1
    assert result.attempts[0].engineering_status == Status.REJECTED_SURFACE_LIMIT
    assert result.attempts[0].retry_reason is None


def test_no_physical_thermal_root_does_not_retry():
    inputs = engineering_inputs().model_copy(update={
        "mode": "solve_return",
        "sigma_k": None,
        "theta_supply_c": 21.1,
    })
    result = assess_with_automatic_split_retry(
        requested(4000, 3000, 1), inputs
    )
    assert result.status == "FAILED_NO_ENGINEERING_FEASIBLE_CANDIDATE"
    assert len(result.attempts) == 1
    assert result.attempts[0].engineering_status == Status.REJECTED_NO_PHYSICAL_THERMAL_ROOT
    assert result.attempts[0].retry_reason is None


def test_numerical_solver_failure_does_not_retry():
    with patch.object(
        kernel,
        "solve_thermal",
        side_effect=kernel.NumericalSolverFailure("synthetic numerical failure"),
    ):
        result = assess_with_automatic_split_retry(
            requested(4000, 3000, 1), engineering_inputs()
        )
    assert result.status == "FAILED_NO_ENGINEERING_FEASIBLE_CANDIDATE"
    assert len(result.attempts) == 1
    assert result.attempts[0].engineering_status == Status.REJECTED_NUMERICAL_CALCULATION
    assert result.attempts[0].retry_reason is None


def test_retry_exhaustion_stops_at_three_circuits():
    request, inputs = pressure_attempt_fixture()
    common = CommonCircuitInputs(**{
        **inputs.common_circuit.model_dump(),
        "manufacturer_max_circuit_pressure_pa": 1.0,
    })
    inputs = UFHEngineeringIntegrationInputs(**{
        **inputs.model_dump(), "common_circuit": common,
    })
    result = assess_with_automatic_split_retry(request, inputs)
    assert result.status == "FAILED_NO_ENGINEERING_FEASIBLE_CANDIDATE"
    assert [a.requested_circuit_count for a in result.attempts] == [2, 3]
    assert [a.actual_circuit_count for a in result.attempts] == [2, 3]
    assert "MAX_CIRCUIT_COUNT_REACHED" in result.diagnostics
    assert len(result.attempts) <= 3


def test_balanceability_failure_is_not_speculatively_split():
    request = requested(7100, 3200, 2)
    inputs = engineering_inputs()
    control = valve(1.5)
    common = CommonCircuitInputs(**{
        **inputs.common_circuit.model_dump(), "control": control,
    })
    inputs = UFHEngineeringIntegrationInputs(**{
        **inputs.model_dump(), "common_circuit": common,
    })
    result = assess_with_automatic_split_retry(request, inputs)
    assert result.status == "FAILED_NO_ENGINEERING_FEASIBLE_CANDIDATE"
    assert len(result.attempts) == 1
    assert result.attempts[0].engineering_status == Status.REJECTED_BALANCEABILITY
    assert result.attempts[0].retry_reason is None


def test_retry_attempt_sequence_and_digest_are_deterministic():
    request, inputs = pressure_attempt_fixture()
    first = assess_with_automatic_split_retry(request, inputs)
    second = assess_with_automatic_split_retry(request, inputs)
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
