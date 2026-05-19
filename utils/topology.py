from __future__ import annotations

from shapely.geometry import LineString, MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import nearest_points, unary_union


def _flatten_polygons(geom: BaseGeometry) -> list[Polygon]:
    """Extract only polygon parts from arbitrary Shapely geometry."""
    if geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    if isinstance(geom, MultiPolygon):
        return list(geom.geoms)
    if hasattr(geom, "geoms"):
        result: list[Polygon] = []
        for part in geom.geoms:
            result.extend(_flatten_polygons(part))
        return result
    return []


def _to_polygons(geometry: BaseGeometry, min_bridge_width: float) -> list[Polygon]:
    """Convert line/curve geometry to polygonal islands via positive buffer."""
    width = max(0.01, min_bridge_width / 2)
    buffered = geometry.buffer(width, cap_style=2, join_style=2)
    return _flatten_polygons(buffered)


def _connect_components(polygons: list[Polygon], min_bridge_width: float) -> BaseGeometry:
    if not polygons:
        return unary_union([])

    remaining = polygons[1:]
    connected: BaseGeometry = polygons[0]
    bridge_radius = max(0.01, min_bridge_width / 2)

    while remaining:
        best_idx = 0
        best_dist = float("inf")
        best_bridge: BaseGeometry | None = None

        for idx, poly in enumerate(remaining):
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
    """Connect disconnected islands by bridges with given minimal width."""
    if geometry.is_empty:
        return geometry

    polygons = _to_polygons(geometry, min_bridge_width)
    if len(polygons) <= 1:
        return geometry

    connected_poly = _connect_components(polygons, min_bridge_width)
    return connected_poly.boundary


def validate_connectivity(geometry: BaseGeometry, min_bridge_width: float = 1.0) -> bool:
    """True when geometry is one connected printable island after buffering."""
    if geometry.is_empty:
        return False

    polygons = _to_polygons(geometry, min_bridge_width)
    if not polygons:
        return False

    merged = unary_union(polygons)
    if isinstance(merged, Polygon):
        return True
    if isinstance(merged, MultiPolygon):
        return len(merged.geoms) == 1
    flat = _flatten_polygons(merged)
    return len(flat) == 1
