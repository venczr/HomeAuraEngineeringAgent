"""OR-Tools CP-SAT optimization layer.

This layer only selects among prepared candidates; it never builds geometry.
It chooses, for every room, exactly one coverage variant (a set of independent
circuits) and, for every chosen circuit, one supply route and one return route,
subject to:

* per-circuit estimated total length <= ``limit_m`` (90 m);
* per-segment pipe occupancy (each selected supply or return passing through a
  segment counts as one pipe; supply and return are separate entities);
* manifold port budget;
* pre-listed forbidden geometric combinations.

The solver status (OPTIMAL / FEASIBLE / INFEASIBLE / UNKNOWN) is returned
separately from any physical validity flags.  OPTIMAL never implies a
physically valid route.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from ortools.sat.python import cp_model


@dataclass
class OptimizationProblem:
    variants: dict[str, list[list[int]]]          # room -> variants -> circuit coverages (m)
    doors: dict[str, list[str]]                   # room -> door ids
    route_options: dict[str, list[tuple[int, tuple[str, ...]]]]  # door -> [(length_m, segments)]
    segments: dict[str, int]                      # segment -> pipe capacity
    manifold_ports: int = 32
    limit_m: int = 90
    forbidden_variants: list[tuple[str, int]] = field(default_factory=list)


@dataclass
class OptimizationResult:
    status: str
    assignment: dict[str, Any] = field(default_factory=dict)
    segment_occupancy: dict[str, int] = field(default_factory=dict)
    objective_value: float | None = None
    rejection_log: list[str] = field(default_factory=list)


def _solve(problem: OptimizationProblem, extra_forbidden: list[tuple[str, int]]) -> OptimizationResult:
    model = cp_model.CpModel()

    circuits = []  # (room, v, c, coverage)
    for room, vs in problem.variants.items():
        for v, covs in enumerate(vs):
            for c, cov in enumerate(covs):
                circuits.append((room, v, c, cov))

    x = {(room, v): model.NewBoolVar(f"x_{room}_{v}")
         for room, vs in problem.variants.items() for v in range(len(vs))}

    y = {}  # (room, v, c, door, opt_idx, flow) -> BoolVar ; flow in {0:supply, 1:return}
    for room, v, c, _cov in circuits:
        for door in problem.doors[room]:
            for opt_idx in range(len(problem.route_options[door])):
                y[(room, v, c, door, opt_idx, 0)] = model.NewBoolVar(f"s_{room}_{v}_{c}_{door}_{opt_idx}")
                y[(room, v, c, door, opt_idx, 1)] = model.NewBoolVar(f"r_{room}_{v}_{c}_{door}_{opt_idx}")

    # 1. exactly one variant per room
    for room, vs in problem.variants.items():
        model.Add(sum(x[(room, v)] for v in range(len(vs))) == 1)

    # 2. each circuit of the chosen variant: exactly one supply and one return route
    for room, v, c, cov in circuits:
        s_terms = [y[(room, v, c, d, i, 0)] for d in problem.doors[room]
                   for i in range(len(problem.route_options[d]))]
        r_terms = [y[(room, v, c, d, i, 1)] for d in problem.doors[room]
                   for i in range(len(problem.route_options[d]))]
        model.Add(sum(s_terms) == 1).OnlyEnforceIf(x[(room, v)])
        model.Add(sum(s_terms) == 0).OnlyEnforceIf(x[(room, v)].Not())
        model.Add(sum(r_terms) == 1).OnlyEnforceIf(x[(room, v)])
        model.Add(sum(r_terms) == 0).OnlyEnforceIf(x[(room, v)].Not())

    # 3. length <= limit per circuit
    for room, v, c, cov in circuits:
        supply_len = sum(problem.route_options[d][i][0] * y[(room, v, c, d, i, 0)]
                         for d in problem.doors[room] for i in range(len(problem.route_options[d])))
        return_len = sum(problem.route_options[d][i][0] * y[(room, v, c, d, i, 1)]
                         for d in problem.doors[room] for i in range(len(problem.route_options[d])))
        model.Add(cov + supply_len + return_len <= problem.limit_m)

    # 4. per-segment occupancy (supply and return counted separately)
    occupancy = {seg: 0 for seg in problem.segments}
    for room, v, c, _cov in circuits:
        for d in problem.doors[room]:
            for i, (_len, segs) in enumerate(problem.route_options[d]):
                for flow in (0, 1):
                    for seg in segs:
                        occupancy[seg] += y[(room, v, c, d, i, flow)]
    for seg, cap in problem.segments.items():
        model.Add(occupancy[seg] <= cap)

    # 5. manifold port budget: one supply + one return port per selected circuit
    port_use = 0
    for room, v, c, _cov in circuits:
        port_use += x[(room, v)]
    model.Add(2 * port_use <= problem.manifold_ports)

    # 6. forbidden variant combinations
    for room, v in problem.forbidden_variants + extra_forbidden:
        if (room, v) in x:
            model.Add(x[(room, v)] == 0)

    transit = []
    for room, v, c, _cov in circuits:
        for d in problem.doors[room]:
            for i, (length, _segs) in enumerate(problem.route_options[d]):
                transit.append(length * y[(room, v, c, d, i, 0)])
                transit.append(length * y[(room, v, c, d, i, 1)])
    model.Minimize(sum(transit))

    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    status_name = {cp_model.FEASIBLE: "FEASIBLE", cp_model.OPTIMAL: "OPTIMAL",
                   cp_model.INFEASIBLE: "INFEASIBLE", cp_model.UNKNOWN: "UNKNOWN"}[status]

    result = OptimizationResult(status=status_name)
    if status in (cp_model.FEASIBLE, cp_model.OPTIMAL):
        result.objective_value = solver.ObjectiveValue()
        for room, vs in problem.variants.items():
            for v in range(len(vs)):
                if solver.Value(x[(room, v)]) == 1:
                    result.assignment[room] = {"variant": v, "circuits": []}
        for room, v, c, cov in circuits:
            if solver.Value(x[(room, v)]) != 1:
                continue
            sd = rd = None
            for d in problem.doors[room]:
                for i in range(len(problem.route_options[d])):
                    if solver.Value(y[(room, v, c, d, i, 0)]) == 1:
                        sd = (d, i)
                    if solver.Value(y[(room, v, c, d, i, 1)]) == 1:
                        rd = (d, i)
            result.assignment[room]["circuits"].append(
                {"coverage": cov, "supply": sd, "return": rd}
            )
        for seg in problem.segments:
            result.segment_occupancy[seg] = int(solver.Value(occupancy[seg]))
    return result


def solve(problem: OptimizationProblem) -> OptimizationResult:
    return _solve(problem, [])


def optimize_with_feedback(
    problem: OptimizationProblem,
    validate: Callable[[OptimizationResult], tuple[bool, str]],
    *,
    max_iterations: int = 10,
) -> OptimizationResult:
    """Solver <-> physical-validator loop.

    ``validate`` inspects a solved assignment and returns ``(accepted, reason)``.
    When it rejects a combination the offending (room, variant) is added as a
    forbidden constraint and the solver is re-run, up to ``max_iterations``.
    """
    extra_forbidden: list[tuple[str, int]] = []
    log: list[str] = []
    for _ in range(max_iterations):
        result = _solve(problem, extra_forbidden)
        if result.status in ("INFEASIBLE", "UNKNOWN"):
            result.rejection_log = list(log)
            return result
        accepted, reason = validate(result)
        if accepted:
            result.rejection_log = list(log)
            return result
        # forbid the whole room's chosen variant that failed physical validation
        room = reason
        variant = result.assignment.get(room, {}).get("variant")
        if room is not None and variant is not None and (room, variant) not in extra_forbidden:
            extra_forbidden.append((room, variant))
            log.append(f"reject {room} variant {variant}: {reason}")
    result = _solve(problem, extra_forbidden)
    result.rejection_log = list(log)
    return result


__all__ = [
    "OptimizationProblem",
    "OptimizationResult",
    "solve",
    "optimize_with_feedback",
]
