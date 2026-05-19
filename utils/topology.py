from __future__ import annotations

from shapely.geometry import LineString
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union


def ensure_connected(geometry: BaseGeometry, min_bridge_width: float) -> BaseGeometry:
    """Ensure all disconnected islands are linked by minimal bridges."""
    if geometry.is_empty:
        return geometry

    buffered = geometry.buffer(min_bridge_width / 2, cap_style=2, join_style=2)
    if buffered.geom_type == "MultiPolygon":
        polys = list(buffered.geoms)
    elif buffered.geom_type == "Polygon":
        polys = [buffered]
    else:
        return geometry

    bridges = []
    for i in range(len(polys) - 1):
        a = polys[i].centroid
        b = polys[i + 1].centroid
        bridges.append(LineString([a, b]).buffer(min_bridge_width / 2, cap_style=2))

    merged = unary_union([buffered, *bridges])
    return merged.boundary


def validate_connectivity(geometry: BaseGeometry) -> bool:
    if geometry.is_empty:
        return False
    buffered = geometry.buffer(0.1)
    if buffered.geom_type == "MultiPolygon":
        return len(buffered.geoms) == 1
    return True
