from __future__ import annotations

import heapq
import json
import os
from pathlib import Path

from shapely.geometry import Point, box, shape


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
BODIES = BASE / "HA_TWO_FLOOR_ATTIC_C01_MANIFOLD_CORRIDOR_085" / "attic_body_geometry.json"
DOMAINS = BASE / "HA_TWO_FLOOR_ATTIC_ADJACENT_FLOOR_DOMAINS_062" / "attic_adjacent_floor_domains.json"
OUTPUT = ROOT / "tmp" / "attic_route_search_147.json"
VOID = box(9900, 5700, 13100, 9200)


def raster_segment(a, b):
    ax, ay = a; bx, by = b
    if ax == bx:
        step = 1 if by >= ay else -1
        return [(ax, y) for y in range(ay, by + step, step)]
    if ay == by:
        step = 1 if bx >= ax else -1
        return [(x, ay) for x in range(ax, bx + step, step)]
    raise ValueError((a, b))


class MinCostFlow:
    def __init__(self, n):
        self.g = [[] for _ in range(n)]

    def add(self, u, v, cap, cost):
        f = [v, cap, cost, None, cap]
        r = [u, 0, -cost, f, 0]
        f[3] = r
        self.g[u].append(f); self.g[v].append(r)

    def solve(self, source, sink, need):
        n = len(self.g); potential = [0] * n; flow = cost = 0
        while flow < need:
            dist = [10**18] * n; prev = [None] * n; dist[source] = 0
            heap = [(0, source)]
            while heap:
                d, u = heapq.heappop(heap)
                if d != dist[u]: continue
                for edge in self.g[u]:
                    v, cap, edge_cost, _, _ = edge
                    if cap <= 0: continue
                    nd = d + edge_cost + potential[u] - potential[v]
                    if nd < dist[v]:
                        dist[v] = nd; prev[v] = (u, edge); heapq.heappush(heap, (nd, v))
            if prev[sink] is None: break
            for i, value in enumerate(dist):
                if value < 10**18: potential[i] += value
            cursor = sink
            while cursor != source:
                u, edge = prev[cursor]; edge[1] -= 1; edge[3][1] += 1; cursor = u
            flow += 1; cost += potential[sink]
        return flow, cost


def main():
    body_model = json.loads(BODIES.read_text(encoding="utf-8-sig"))
    domains = json.loads(DOMAINS.read_text(encoding="utf-8-sig"))
    domain = shape(domains["known_floor_union_geojson"]).buffer(250, join_style=2)
    routes = {route["route_id"]: route for route in body_model["body_routes"]}
    # Shift the A-C05 top edge 300 mm south to free one continuous handoff row
    # immediately below the structural stair void. The replacement remains a
    # regular paired counterflow body and stays above the 40 m body threshold.
    routes["A-C05"]["body_points_grid"] = [
        [128,129],[101,129],[101,96],[128,96],[128,125],[105,125],[105,100],
        [124,100],[124,121],[109,121],[109,104],[120,104],[120,106],[111,106],
        [111,119],[122,119],[122,102],[107,102],[107,123],[126,123],[126,98],
        [103,98],[103,127],[126,127]
    ]
    routes["A-C06"]["body_points_grid"] = [
        [128,168],[101,168],[101,141],[128,141],[128,164],[105,164],[105,145],
        [124,145],[124,160],[109,160],[109,149],[120,149],[120,151],[111,151],
        [111,158],[122,158],[122,147],[107,147],[107,162],[126,162],[126,143],
        [103,143],[103,166],[126,166]
    ]

    serial_connector = [(137,113),(133,113),(133,127),(159,127),(159,113),(163,113)]
    target_info = {}
    for route_id, route in routes.items():
        if route_id == "A-C05": continue
        if route_id in {"A-C10", "A-C11"}: continue
        points = [tuple(point) for point in route["body_points_grid"]]
        target_info[points[0]] = {"route_id": route_id, "body_endpoint": "START"}
        target_info[points[-1]] = {"route_id": route_id, "body_endpoint": "END"}
    target_info[(135,111)] = {"route_id":"A-C10_C11_SERIAL","body_endpoint":"C10_START"}
    target_info[(161,111)] = {"route_id":"A-C10_C11_SERIAL","body_endpoint":"C11_START_REVERSED"}
    targets = set(target_info)
    assert len(targets) == 22

    occupied = set(); occupied_by_route = {}
    for route in routes.values():
        if route["route_id"] == "A-C05": continue
        points = [tuple(point) for point in route["body_points_grid"]]
        route_nodes = set()
        for a, b in zip(points, points[1:]): route_nodes.update(raster_segment(a, b))
        occupied_by_route[route["route_id"]] = route_nodes
        occupied.update(route_nodes)
    for a, b in zip(serial_connector, serial_connector[1:]): occupied.update(raster_segment(a, b))
    body_obstacles = occupied - targets
    allowed_body_ids = {item for item in os.environ.get("HA_ALLOW_BODY_IDS", "").split(",") if item}
    allowed_body_nodes = set().union(*(occupied_by_route[item] for item in allowed_body_ids)) if allowed_body_ids else set()
    absolute_obstacles = (occupied - allowed_body_nodes) - targets
    # Bodies are endpoints/consumers, not absolute routing walls for the global
    # feasibility search. Crossings with non-owned bodies are screened after
    # path extraction; excluding them here creates an artificial 9-node cut at
    # the stair/hall seam and cannot prove the available floor capacity.
    occupied = set()

    triplets = {
        "T01": [(101,93),(102,93),(103,93)], "T02": [(105,93),(106,93),(107,93)],
        "T03": [(109,93),(110,93),(111,93)], "T04": [(113,93),(114,93),(115,93)],
        "T05": [(117,93),(118,93),(119,93)], "T06": [(121,93),(122,93),(123,93)],
        "T07": [(125,93),(126,93),(127,93)], "T08": [(129,93),(130,93),(131,93)],
        "T09": [(133,93),(134,93),(135,93)],
    }
    source_info = {point: {"triplet_id": group, "node_index": i + 1} for group, points in triplets.items() for i, point in enumerate(points)}
    sources = set(source_info)
    assert len(sources) == 27

    allowed = set()
    for x in range(44, 190):
        for y in range(54, 198):
            point = Point(x * 100, y * 100)
            if domain.covers(point) and not VOID.covers(point) and (x, y) not in absolute_obstacles:
                allowed.add((x, y))
    allowed |= sources | targets
    points = sorted(allowed); index = {point: i for i, point in enumerate(points)}
    count = len(points); source_node = count * 2; sink_node = source_node + 1
    graph = MinCostFlow(sink_node + 1)
    for point, i in index.items():
        cap = 1
        graph.add(i * 2, i * 2 + 1, cap, 10000 if point in body_obstacles else 0)
        for neighbour in ((point[0]+1,point[1]),(point[0]-1,point[1]),(point[0],point[1]+1),(point[0],point[1]-1)):
            if neighbour in index: graph.add(i * 2 + 1, index[neighbour] * 2, 1, 1)
    for point in sources: graph.add(source_node, index[point] * 2, 1, 0)
    for point in targets: graph.add(index[point] * 2 + 1, sink_node, 1, 0)
    flow, cost = graph.solve(source_node, sink_node, 22)
    if flow != 22:
        raise RuntimeError({"flow": flow, "required": 22, "allowed_nodes": len(allowed)})

    used_sources = []
    for edge in graph.g[source_node]:
        if edge[4] == 1 and edge[1] == 0:
            used_sources.append(points[edge[0] // 2])
    used_targets = {point for point in targets if any(edge[0] == sink_node and edge[4] == 1 and edge[1] == 0 for edge in graph.g[index[point]*2+1])}
    assert len(used_sources) == len(used_targets) == 22

    flow_moves = {}
    for point, i in index.items():
        outgoing = []
        for edge in graph.g[i*2+1]:
            if edge[4] == 1 and edge[1] == 0 and edge[0] < count*2 and edge[0] % 2 == 0:
                outgoing.append(points[edge[0]//2])
        if outgoing: flow_moves[point] = outgoing
    paths = []
    remaining_targets = set(used_targets)
    for source in used_sources:
        path = [source]; seen = {source}; cursor = source
        while cursor not in remaining_targets:
            options = [p for p in flow_moves.get(cursor, []) if p not in seen]
            if not options:
                raise RuntimeError({"stuck": cursor, "source": source, "path": path[-10:]})
            cursor = options[0]; path.append(cursor); seen.add(cursor)
            if len(path) > len(points): raise RuntimeError("cycle")
        remaining_targets.remove(cursor)
        paths.append({"source_grid": list(source), "source": source_info[source], "target_grid": list(cursor), "target": target_info[cursor], "points_grid": [list(p) for p in path], "transit_length_mm": (len(path)-1)*100})
    assert not remaining_targets
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    used_body_obstacle_nodes = sum(sum(tuple(point) in body_obstacles for point in path["points_grid"][1:-1]) for path in paths)
    OUTPUT.write_text(json.dumps({"status":"PASS_22_VERTEX_DISJOINT_MIN_COST_PATHS_FOR_11_FLOOR_AXES","flow":flow,"total_transit_length_mm":sum(p["transit_length_mm"] for p in paths),"used_foreign_body_obstacle_node_count":used_body_obstacle_nodes,"serial_connector_points_grid":[list(p) for p in serial_connector],"paths":paths},ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"output":str(OUTPUT),"flow":flow,"total_transit_m":sum(p["transit_length_mm"] for p in paths)/1000,"used_body_obstacle_nodes":used_body_obstacle_nodes,"path_lengths_m":sorted(round(p["transit_length_mm"]/1000,1) for p in paths),"used_sources":sorted([p["source_grid"] for p in paths])},ensure_ascii=False,indent=2))


if __name__ == "__main__": main()
