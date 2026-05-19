from __future__ import annotations

import math
from shapely.affinity import rotate
from shapely.geometry import LineString, MultiLineString
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from generators.base import BaseGenerator
from utils.models import CanvasParams, GenerationParams


class GeometricGenerator(BaseGenerator):
    def _grid(self, w: float, h: float, step: float) -> BaseGeometry:
        lines = []
        x = 0.0
        while x <= w:
            lines.append(LineString([(x, 0), (x, h)]))
            x += step
        y = 0.0
        while y <= h:
            lines.append(LineString([(0, y), (w, y)]))
            y += step
        return MultiLineString(lines)

    def _triangles(self, w: float, h: float, step: float) -> BaseGeometry:
        lines = []
        y = 0.0
        while y <= h:
            x = 0.0
            while x <= w:
                lines.append(LineString([(x, y), (x + step / 2, y + step), (x + step, y), (x, y)]))
                x += step
            y += step
        return MultiLineString(lines)

    def _circles(self, w: float, h: float, step: float) -> BaseGeometry:
        items = []
        y = step / 2
        while y <= h:
            x = step / 2
            while x <= w:
                items.append(LineString(list(__import__('shapely').geometry.Point(x, y).buffer(step * 0.35).boundary.coords)))
                x += step
            y += step
        return unary_union(items)

    def _hex(self, cx: float, cy: float, r: float) -> LineString:
        pts = []
        for i in range(6):
            a = math.radians(60 * i)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        pts.append(pts[0])
        return LineString(pts)

    def _honeycomb(self, w: float, h: float, size: float) -> BaseGeometry:
        geoms = []
        dx = size * 1.5
        dy = size * math.sqrt(3)
        row = 0
        y = size
        while y < h:
            offset = size * 0.75 if row % 2 else 0
            x = size + offset
            while x < w:
                geoms.append(self._hex(x, y, size * 0.6))
                x += dx
            y += dy / 2
            row += 1
        return unary_union(geoms)

    def generate(self, canvas: CanvasParams, params: GenerationParams) -> BaseGeometry:
        step = max(5.0, params.cell_size / max(0.2, params.density))
        shapes = [
            self._grid(canvas.width, canvas.height, step),
            self._circles(canvas.width, canvas.height, step),
            self._honeycomb(canvas.width, canvas.height, step / 2),
            self._triangles(canvas.width, canvas.height, step),
        ]
        geom = unary_union(shapes)
        return rotate(geom, params.rotation, origin=(canvas.width / 2, canvas.height / 2))
