from __future__ import annotations

from agent.ufh_cp_sat_optimizer import OptimizationProblem, optimize_with_feedback, solve


def _problem(**overrides):
    variants = {
        "R1": [[75], [37, 37]],
        "R2": [[60], [30, 30]],
        "R3": [[80], [40, 40]],
    }
    doors = {"R1": ["R1e", "R1w"], "R2": ["R2"], "R3": ["R3e", "R3w"]}
    route_options = {
        "R1e": [(5, ("E",)), (15, ("W", "X"))],
        "R1w": [(11, ("W",)), (15, ("E", "X"))],
        "R2": [(10, ("E", "M")), (20, ("W", "X", "M"))],
        "R3e": [(12, ("E", "M")), (22, ("W", "X", "M"))],
        "R3w": [(15, ("W",)), (19, ("E", "X"))],
    }
    segments = {"E": 10, "W": 10, "M": 10, "X": 10}
    params = dict(variants=variants, doors=doors, route_options=route_options, segments=segments, limit_m=90)
    params.update(overrides)
    return OptimizationProblem(**params)


def test_scenario_a_feasible() -> None:
    result = solve(_problem())
    assert result.status in ("OPTIMAL", "FEASIBLE")
    assert result.assignment["R1"]["variant"] == 0
    assert result.assignment["R2"]["variant"] == 0
    assert result.assignment["R3"]["variant"] == 1  # R3 needs two circuits


def test_scenario_b_alternatives_relieve_congested_corridor() -> None:
    # E can hold 4 pipes; R1 (2) + R2 (2) already fill it, so R3 must go west.
    result = solve(_problem(segments={"E": 4, "W": 4, "M": 4, "X": 10}))
    assert result.status in ("OPTIMAL", "FEASIBLE")
    assert result.segment_occupancy["E"] <= 4
    assert result.segment_occupancy["W"] >= 4


def test_scenario_c_infeasible_by_length() -> None:
    result = solve(_problem(variants={"R1": [[75]], "R2": [[60]], "R3": [[85]]}))
    assert result.status == "INFEASIBLE"


def test_scenario_d_infeasible_by_capacity() -> None:
    # M is the only passage to R2 and must carry its 2 pipes.
    result = solve(_problem(segments={"E": 10, "W": 10, "M": 1, "X": 10}))
    assert result.status == "INFEASIBLE"


def test_supply_and_return_choose_different_routes() -> None:
    # Force an asymmetric solution: R1's only circuit cannot put both supply and
    # return on E (capacity 1), and E+W is shorter than W+W, so the solver
    # chooses different doors for supply and return.
    result = solve(_problem(
        variants={"R1": [[60]]},
        doors={"R1": ["R1e", "R1w"]},
        segments={"E": 1, "W": 10, "M": 10, "X": 10},
    ))
    assert result.status in ("OPTIMAL", "FEASIBLE")
    circuit = result.assignment["R1"]["circuits"][0]
    assert circuit["supply"][0] != circuit["return"][0]


def test_feedback_loop_rejects_and_resolves() -> None:
    # Physical validator rejects R1 variant 0 once; the loop forbids it and
    # re-solves, landing on R1 variant 1.
    rejected = []

    def validate(result):
        if result.assignment.get("R1", {}).get("variant") == 0:
            rejected.append("R1")
            return False, "R1"
        return True, ""

    result = optimize_with_feedback(_problem(), validate, max_iterations=10)
    assert result.assignment["R1"]["variant"] == 1
    assert "R1" in rejected
    assert result.rejection_log


def test_optimal_does_not_imply_physical_valid() -> None:
    result = solve(_problem())
    assert result.status in ("OPTIMAL", "FEASIBLE")
    # the optimizer only asserts discreteness; physical validity flags are absent
    assert "FULL_CIRCUIT_VALID" not in result.assignment
