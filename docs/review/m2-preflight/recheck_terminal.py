"""Read-only independent numeric recheck; writes JSON to stdout only.

Run: python recheck_terminal.py
Requires numpy and shapely. Does not import the reference builder, validator,
or writing unittest harness. This does not approve the terminal-zone contract.
"""
import json
import math
from pathlib import Path

import numpy as np
import shapely

ROOT = Path(__file__).resolve().parent
EPS = 0.001
GRID = 10


def endpoint(p, final=False):
    if p["kind"] == "line":
        return p["b"] if final else p["a"]
    a = p["start"] + (p["sweep"] if final else 0)
    return [p["c"][0] + p["r"] * math.cos(a),
            p["c"][1] + p["r"] * math.sin(a)]


def tangent(p, final=False):
    if p["kind"] == "line":
        dx, dy = (p["b"][i] - p["a"][i] for i in (0, 1))
        length = math.hypot(dx, dy)
        return [dx / length, dy / length]
    a = p["start"] + (p["sweep"] if final else 0)
    sign = math.copysign(1, p["sweep"])
    return [-sign * math.sin(a), sign * math.cos(a)]


def length(p):
    return (math.dist(p["a"], p["b"]) if p["kind"] == "line"
            else p["r"] * abs(p["sweep"]))


def samples(p, max_chord_length=None):
    n = (1 if p["kind"] == "line" else
         max(1, math.ceil(abs(p["sweep"]) /
             (2 * math.acos(1 - EPS / p["r"])))))
    if max_chord_length is not None:
        n = max(n, math.ceil(length(p) / max_chord_length))
    if p["kind"] == "line":
        return [[p["a"][j] + (p["b"][j] - p["a"][j]) * i / n
                 for j in (0, 1)] for i in range(n + 1)]
    return [[p["c"][0] + p["r"] * math.cos(p["start"] + i * p["sweep"] / n),
             p["c"][1] + p["r"] * math.sin(p["start"] + i * p["sweep"] / n)]
            for i in range(n + 1)]


def geometry(curves):
    points = []
    for primitive in curves:
        vertices = samples(primitive)
        points.extend(vertices if not points else vertices[1:])
    return shapely.LineString(points)


def nonlocal_clearance(curves, od):
    """Conservative chord pairs; local exemption is valid only with G1/R80.

    Every excluded chord pair has total intrinsic span <=2*OD. For OD<=16
    and R>=80, turning over that span is <=0.4 radians. The bounded-curvature
    local tube cannot return onto itself in this neighbourhood. No complete
    primitive, even an adjacent arc, is exempted.
    """
    prerequisites = (od <= 16 and all(p["r"] >= 80 for p in curves
                     if p["kind"] == "arc") and
                     all(math.dist(endpoint(a, True), endpoint(b)) < 1e-6 and
                         math.dist(tangent(a, True), tangent(b)) < 1e-6
                         for a, b in zip(curves, curves[1:])))
    if not prerequisites:
        return {"status": "INDETERMINATE", "reason": "Local-tube prerequisites failed"}
    chords, starts, finishes = [], [], []
    cursor = 0.0
    for primitive in curves:
        vertices = samples(primitive, 4)
        step = length(primitive) / (len(vertices) - 1)
        for i in range(len(vertices) - 1):
            chords.append(shapely.LineString(vertices[i:i + 2]))
            starts.append(cursor + i * step)
            finishes.append(cursor + (i + 1) * step)
        cursor += length(primitive)
    array = np.asarray(chords, dtype=object)
    first, second = shapely.STRtree(chords).query(
        chords, predicate="dwithin", distance=od + 2 * EPS + 1e-6)
    selected = ((first < second) &
                ((np.asarray(finishes)[second] - np.asarray(starts)[first]) > 2 * od))
    first, second = first[selected], second[selected]
    if not len(first):
        return {"status": "PASS", "axis_distance_lower_bound_mm": od + 1e-6,
                "chord_count": len(chords), "local_arclength_exemption_mm": 2 * od}
    distances = shapely.distance(array[first], array[second])
    d = float(np.min(distances))
    return {"status": ("PASS" if d - 2 * EPS >= od else
                       "FAIL" if d + 2 * EPS < od else "INDETERMINATE"),
            "axis_distance_interval_mm": [max(0, d - 2 * EPS), d + 2 * EPS],
            "chord_count": len(chords), "local_arclength_exemption_mm": 2 * od}


def main():
    data = json.loads((ROOT / "terminal-transition-candidate.json").read_text())
    saved = json.loads((ROOT / "terminal-transition-results.json").read_text())
    curves, fixture = data["curves"], data["fixture"]
    route = geometry(curves)
    floor = shapely.Polygon(fixture["polygon"], fixture.get("holes", []))
    minx, miny, maxx, maxy = floor.bounds
    assert not fixture.get("holes") and floor.equals(shapely.box(minx, miny, maxx, maxy))
    nx, ny = math.ceil((maxx - minx) / GRID), math.ceil((maxy - miny) / GRID)
    xx, yy = np.meshgrid(np.linspace(minx, maxx, nx + 1), np.linspace(miny, maxy, ny + 1))
    points = np.column_stack([xx.ravel(), yy.ravel()])
    distances = shapely.distance(shapely.points(points), route)
    index = int(np.argmax(distances))
    maximum = float(distances[index])
    bound = maximum + math.hypot((maxx - minx) / nx, (maxy - miny) / ny) / 2 + EPS
    clearance = fixture["minimum_pipe_surface_wall_clearance_mm"] + fixture["pipe_od_mm"] / 2
    metrics = {
        "exact_length_mm": sum(length(p) for p in curves),
        "radii_mm": sorted(set(p["r"] for p in curves if p["kind"] == "arc")),
        "axis_wall_distance_lower_bound_mm": route.distance(floor.boundary) - EPS,
        "sampled_max_distance_mm": maximum,
        "sampled_max_witness": points[index].tolist(),
        "max_distance_upper_bound_mm": bound,
        "point_count": len(points), "grid_step_mm": GRID, "sagitta_bound_mm": EPS,
        "pipe_clearance": nonlocal_clearance(curves, fixture["pipe_od_mm"]),
    }
    checks = {
        "endpoints": math.dist(endpoint(curves[0]), fixture["supply"]) < 1e-6 and
                     math.dist(endpoint(curves[-1], True), fixture["return"]) < 1e-6,
        "endpoint_tangents": math.dist(tangent(curves[0]), fixture["supply_traversal_tangent"]) < 1e-6 and
                             math.dist(tangent(curves[-1], True), fixture["return_traversal_tangent"]) < 1e-6,
        "continuity": all(math.dist(endpoint(a, True), endpoint(b)) < 1e-6
                          for a, b in zip(curves, curves[1:])),
        "tangency": all(math.dist(tangent(a, True), tangent(b)) < 1e-6
                        for a, b in zip(curves, curves[1:])),
        "radius": min(metrics["radii_mm"]) >= fixture["minimum_radius_mm"],
        "length": metrics["exact_length_mm"] <= fixture["maximum_length_mm"],
        "wall_clearance": floor.covers(route) and metrics["axis_wall_distance_lower_bound_mm"] >= clearance,
        "maximum_distance": bound <= fixture["maximum_nearest_axis_distance_mm"],
    }
    matches = all(abs(metrics[key] - saved["refinement"][key]) < 1e-6 for key in
                  ("sampled_max_distance_mm", "max_distance_upper_bound_mm"))
    print(json.dumps({"status": "PartialGeometryOnly", "export_allowed": False,
                      "matches_saved_refinement": matches, "physical_checks": checks,
                      "metrics": metrics,
                      "unresolved": ["Original morphology FAIL", "Original pitch FAIL",
                                     "20mm terminal strips have no verified zone contract"]}, indent=2))
    return 0 if matches and all(checks.values()) and metrics["pipe_clearance"]["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
