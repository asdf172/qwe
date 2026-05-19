from __future__ import annotations

from pathlib import Path
from shapely.geometry import LineString, MultiLineString
from shapely.geometry.base import BaseGeometry
import svgwrite


def _iter_lines(geom: BaseGeometry):
    if geom.geom_type == "LineString":
        yield geom
    elif geom.geom_type == "MultiLineString":
        for g in geom.geoms:
            yield g
    elif hasattr(geom, "boundary"):
        yield from _iter_lines(geom.boundary)


def export_stencil_svg(geometry: BaseGeometry, width: float, height: float, units: str, path: str = "stencil.svg") -> Path:
    out = Path(path)
    dwg = svgwrite.Drawing(str(out), size=(f"{width}{units}", f"{height}{units}"), profile="tiny")
    group = dwg.g(stroke="black", fill="none", stroke_width=1)
    for line in _iter_lines(geometry):
        if not isinstance(line, LineString):
            continue
        points = list(line.coords)
        if len(points) < 2:
            continue
        d = "M " + " L ".join(f"{x:.2f},{y:.2f}" for x, y in points)
        group.add(dwg.path(d=d, fill="none"))
    dwg.add(group)
    dwg.save()
    return out
