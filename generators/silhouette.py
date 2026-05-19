from __future__ import annotations

from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image
from shapely.affinity import scale, translate
from shapely.geometry import LineString, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from generators.base import BaseGenerator
from utils.models import CanvasParams, GenerationParams, SilhouetteParams


class SilhouetteGenerator(BaseGenerator):
    """Generate silhouette stencil from image contours or fallback primitive shape."""

    def __init__(self) -> None:
        self.image_path: Optional[Path] = None
        self.sil_params = SilhouetteParams()

    def set_image(self, path: str) -> None:
        self.image_path = Path(path)

    def auto_tune(self) -> None:
        """Auto-calibrate thresholds for the loaded image."""
        gray = self._load_gray()
        if gray is None:
            return
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        # Otsu gives stable threshold for many photos and logos
        otsu, _ = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        self.sil_params.threshold = int(otsu)
        med = float(np.median(blur))
        self.sil_params.canny_low = int(max(10, 0.66 * med))
        self.sil_params.canny_high = int(min(255, 1.33 * med))

    def _default_shape(self) -> BaseGeometry:
        poly = Polygon([(10, 60), (50, 10), (90, 60), (70, 110), (30, 110)])
        eyes = [
            Polygon([(35, 50), (42, 50), (42, 58), (35, 58)]),
            Polygon([(58, 50), (65, 50), (65, 58), (58, 58)]),
        ]
        return poly.boundary.union(unary_union([e.boundary for e in eyes]))

    def _load_gray(self) -> Optional[np.ndarray]:
        if not self.image_path or not self.image_path.exists():
            return None
        try:
            img = Image.open(self.image_path).convert("L")
            return np.array(img)
        except Exception:
            return None

    def _trace_image(self, canvas: CanvasParams) -> BaseGeometry:
        gray = self._load_gray()
        if gray is None:
            return self._default_shape()

        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 2)
        _, fixed = cv2.threshold(gray, self.sil_params.threshold, 255, cv2.THRESH_BINARY_INV)
        _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        binary = cv2.bitwise_or(adaptive, cv2.bitwise_or(fixed, otsu))

        kernel = np.ones((3, 3), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)

        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        lines: list[LineString] = []
        h, w = gray.shape[:2]
        min_area = max(20.0, (w * h) * 0.0005)
        for c in contours:
            area = cv2.contourArea(c)
            if area < min_area:
                continue
            peri = cv2.arcLength(c, True)
            eps = max(0.5, self.sil_params.simplify_tolerance * 0.01 * peri)
            approx = cv2.approxPolyDP(c, eps, True)
            pts = [(float(p[0][0]), float(p[0][1])) for p in approx]
            if len(pts) > 2:
                pts.append(pts[0])
                lines.append(LineString(pts))

        if not lines:
            edges = cv2.Canny(gray, self.sil_params.canny_low, self.sil_params.canny_high)
            contours2, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for c in contours2:
                if cv2.contourArea(c) < min_area:
                    continue
                pts = [(float(p[0][0]), float(p[0][1])) for p in c]
                if len(pts) > 2:
                    pts.append(pts[0])
                    lines.append(LineString(pts))

        if not lines:
            return self._default_shape()

        geom = unary_union(lines)
        minx, miny, maxx, maxy = geom.bounds
        if maxx - minx <= 0 or maxy - miny <= 0:
            return self._default_shape()

        s = min((canvas.width * 0.8) / (maxx - minx), (canvas.height * 0.8) / (maxy - miny))
        geom = scale(geom, xfact=s, yfact=s, origin=(minx, miny))
        minx2, miny2, maxx2, maxy2 = geom.bounds
        return translate(geom, xoff=(canvas.width - (maxx2 - minx2)) / 2 - minx2, yoff=(canvas.height - (maxy2 - miny2)) / 2 - miny2)

    def generate(self, canvas: CanvasParams, params: GenerationParams) -> BaseGeometry:
        del params
        return self._trace_image(canvas)
