from __future__ import annotations

from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from shapely.affinity import scale
from shapely.geometry import LineString, MultiLineString, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from generators.base import BaseGenerator
from utils.models import CanvasParams, GenerationParams, SilhouetteParams


class SilhouetteGenerator(BaseGenerator):
    def __init__(self) -> None:
        self.image_path: Optional[Path] = None
        self.sil_params = SilhouetteParams()

    def set_image(self, path: str) -> None:
        self.image_path = Path(path)

    def _default_shape(self) -> BaseGeometry:
        poly = Polygon([(10, 60), (50, 10), (90, 60), (70, 110), (30, 110)])
        eyes = [Polygon([(35, 50), (42, 50), (42, 58), (35, 58)]), Polygon([(58, 50), (65, 50), (65, 58), (58, 58)])]
        return poly.boundary.union(unary_union([e.boundary for e in eyes]))

    def _trace_image(self, canvas: CanvasParams) -> BaseGeometry:
        if not self.image_path or not self.image_path.exists():
            return self._default_shape()

        image = cv2.imread(str(self.image_path), cv2.IMREAD_GRAYSCALE)
        if image is None:
            return self._default_shape()

        _, binary = cv2.threshold(image, self.sil_params.threshold, 255, cv2.THRESH_BINARY)
        edges = cv2.Canny(binary, self.sil_params.canny_low, self.sil_params.canny_high)
        contours, _ = cv2.findContours(edges, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        lines = []
        for c in contours:
            if len(c) < 3:
                continue
            approx = cv2.approxPolyDP(c, self.sil_params.simplify_tolerance, True)
            pts = [(float(p[0][0]), float(p[0][1])) for p in approx]
            if len(pts) > 2:
                pts.append(pts[0])
                lines.append(LineString(pts))
        if not lines:
            return self._default_shape()
        geom = unary_union(lines)
        minx, miny, maxx, maxy = geom.bounds
        if maxx - minx <= 0 or maxy - miny <= 0:
            return geom
        geom = scale(geom, xfact=(canvas.width * 0.8) / (maxx - minx), yfact=(canvas.height * 0.8) / (maxy - miny), origin=(minx, miny))
        return geom

    def generate(self, canvas: CanvasParams, params: GenerationParams) -> BaseGeometry:
        del params
        return self._trace_image(canvas)
