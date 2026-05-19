from __future__ import annotations

from typing import Iterable

from shapely.geometry import LineString
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union


def _to_polygons(geometry: BaseGeometry, min_bridge_width: float):
    """Convert any input geometry to polygons using a safe positive buffer."""
    width = max(0.01, min_bridge_width / 2)
    buffered = geometry.buffer(width, cap_style=2, join_style=2)
    if buffered.is_empty:
        return []
    if buffered.geom_type == "Polygon":
        return [buffered]
    if buffered.geom_type == "MultiPolygon":
        return list(buffered.geoms)
    if hasattr(buffered, "geoms"):
        return [g for g in buffered.geoms if g.geom_type in {"Polygon", "MultiPolygon"}]
    return []


def _connect_components(polygons: list[BaseGeometry], min_bridge_width: float) -> BaseGeometry:
    if not polygons:
        return unary_union([])

    remaining = polygons[1:]
    connected = polygons[0]
    bridge_radius = max(0.01, min_bridge_width / 2)

    while remaining:
        connected_boundary = connected.boundary
        best_idx = -1
        best_dist = float("inf")
        best_bridge = None

        for idx, poly in enumerate(remaining):
            other_boundary = poly.boundary
            p1, p2 = connected_boundary.interpolate(0, normalized=True), other_boundary.interpolate(0, normalized=True)
            # nearest_points даёт надёжные точки на границах ближайших компонентов
            from shapely.ops import nearest_points

            p1, p2 = nearest_points(connected, poly)
            dist = p1.distance(p2)
            if dist < best_dist:
                best_dist = dist
                best_idx = idx
                best_bridge = LineString([p1, p2]).buffer(bridge_radius, cap_style=2, join_style=2)

        next_poly = remaining.pop(best_idx)
        connected = unary_union([connected, next_poly, best_bridge])

    return connected


def ensure_connected(geometry: BaseGeometry, min_bridge_width: float) -> BaseGeometry:
    """Ensure all disconnected islands are linked by bridges of at least min_bridge_width."""
    if geometry.is_empty:
        return geometry

    polygons = _to_polygons(geometry, min_bridge_width)
    if len(polygons) <= 1:
        return geometry

    connected_poly = _connect_components(polygons, min_bridge_width)
    return connected_poly.boundary


def validate_connectivity(geometry: BaseGeometry, min_bridge_width: float = 1.0) -> bool:
    """Topology check: after buffering, final stencil should have one connected component."""
    if geometry.is_empty:
        return False
    polygons = _to_polygons(geometry, min_bridge_width)
    if not polygons:
        return False
    merged = unary_union(polygons)
    if merged.geom_type == "MultiPolygon":
        return len(merged.geoms) == 1
    return merged.geom_type == "Polygon"
