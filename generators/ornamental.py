from __future__ import annotations

import math
from shapely.affinity import rotate, scale, translate
from shapely.geometry import LineString, MultiLineString, Point
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from generators.base import BaseGenerator
from utils.models import CanvasParams, GenerationParams


class OrnamentalGenerator(BaseGenerator):
    def _flower(self, radius: float = 8.0, petals: int = 6) -> BaseGeometry:
        items = []
        for i in range(petals):
            ang = i * (360.0 / petals)
            p = translate(Point(0, radius * 0.7).buffer(radius, resolution=16).boundary, xoff=0, yoff=0)
            items.append(rotate(p, ang, origin=(0, 0)))
        items.append(Point(0, 0).buffer(radius * 0.45).boundary)
        return unary_union(items)

    def _wave(self, width: float = 30.0) -> BaseGeometry:
        points = [(x, math.sin(x / 5) * 5) for x in range(0, int(width) + 1)]
        return LineString(points)

    def _meander(self, size: float = 22.0) -> BaseGeometry:
        s = size
        return MultiLineString([
            [(0, 0), (s, 0), (s, s), (2 * s, s), (2 * s, -s), (3 * s, -s), (3 * s, 0)],
        ])

    def _arabesque(self, size: float = 10.0) -> BaseGeometry:
        a = Point(0, 0).buffer(size, resolution=32).boundary
        b = translate(Point(0, 0).buffer(size, resolution=32).boundary, xoff=size * 1.2)
        return unary_union([a, b])

    def generate(self, canvas: CanvasParams, params: GenerationParams) -> BaseGeometry:
        motifs = [self._flower(), self._wave(), self._meander(), self._arabesque()]
        geoms: list[BaseGeometry] = []
        x, y = 20.0, 20.0
        for i in range(max(1, params.repeats)):
            motif = motifs[i % len(motifs)]
            motif = scale(motif, xfact=params.scale, yfact=params.scale, origin=(0, 0))
            motif = rotate(motif, params.rotation, origin=(0, 0))
            motif = translate(motif, xoff=x, yoff=y)
            geoms.append(motif)
            x += params.spacing
            if x > canvas.width - 20:
                x = 20
                y += params.spacing
        return unary_union(geoms)
