"""NetworkX alternative-route layer for the building graph.

This is an upper layer of candidate selection: it turns the building's
openings / corridors / risers into an undirected weighted graph and returns up
to ``k`` simple alternative routes (Yen's algorithm via
``networkx.shortest_simple_paths``) between a terminal and the collector.

It does not build the actual corridor geometry; the existing geometric router
(``ufh_building_routing``) remains responsible for materialising a chosen
route inside a corridor / passage.  Each returned candidate only records the
sequence of shared segments, an estimated length, the crossed doors and risers,
and an ``UNVERIFIED`` confirmation status per transition.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

import networkx as nx


@dataclass(frozen=True)
class RouteCandidate:
    route_id: str
    path: tuple[str, ...]
    segments: tuple[str, ...]
    estimated_length_m: float
    doors: tuple[str, ...] = ()
    risers: tuple[str, ...] = ()
    transition_status: str = "UNVERIFIED"

    def as_dict(self) -> dict[str, Any]:
        return {
            "route_id": self.route_id,
            "path": list(self.path),
            "segments": list(self.segments),
            "estimated_length_m": round(self.estimated_length_m, 3),
            "doors": list(self.doors),
            "risers": list(self.risers),
            "transition_status": self.transition_status,
        }


def build_building_graph(
    edges: Iterable[tuple[str, str, dict[str, Any]]],
) -> nx.Graph:
    """Build an undirected weighted graph from ``(u, v, data)`` edges.

    ``data`` may carry ``length`` (metres) and ``segment`` (a shared segment
    id), ``door`` (door id) and ``riser`` (riser id) attributes.
    """
    graph = nx.Graph()
    for u, v, data in edges:
        graph.add_edge(u, v, **data)
    return graph


def alternative_routes(
    graph: nx.Graph,
    source: str,
    target: str,
    *,
    k: int = 2,
    length_attr: str = "length",
    segment_attr: str = "segment",
) -> list[RouteCandidate]:
    """Return up to ``k`` simple alternative routes from ``source`` to ``target``.

    Routes are produced by increasing path length (Yen's algorithm).  A route
    collects the shared segments, doors and risers of the edges it crosses;
    every transition is marked ``UNVERIFIED`` because graph connectivity is not
    proof that a physical opening / penetration exists.
    """
    candidates: list[RouteCandidate] = []
    for index, path in enumerate(nx.shortest_simple_paths(graph, source, target, weight=length_attr)):
        if index >= k:
            break
        segments: list[str] = []
        doors: list[str] = []
        risers: list[str] = []
        length = 0.0
        for u, v in zip(path, path[1:]):
            data = graph[u][v]
            length += float(data.get(length_attr, 0.0))
            seg = data.get(segment_attr)
            if seg:
                segments.append(seg)
            if data.get("door"):
                doors.append(str(data["door"]))
            if data.get("riser"):
                risers.append(str(data["riser"]))
        candidates.append(
            RouteCandidate(
                route_id=f"{source}->{target}#{index}",
                path=tuple(path),
                segments=tuple(dict.fromkeys(segments)),
                estimated_length_m=length,
                doors=tuple(dict.fromkeys(doors)),
                risers=tuple(dict.fromkeys(risers)),
            )
        )
    return candidates


__all__ = ["RouteCandidate", "build_building_graph", "alternative_routes"]
