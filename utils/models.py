from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Units(str, Enum):
    MM = "mm"
    PX = "px"


class StencilType(str, Enum):
    ORNAMENTAL = "Орнаментальный"
    GEOMETRIC = "Геометрический"
    SILHOUETTE = "Силуэтный"


@dataclass(slots=True)
class CanvasParams:
    width: float = 200.0
    height: float = 200.0
    units: Units = Units.MM
    line_thickness: float = 1.0


@dataclass(slots=True)
class GenerationParams:
    stencil_type: StencilType = StencilType.ORNAMENTAL
    repeats: int = 6
    spacing: float = 20.0
    rotation: float = 0.0
    scale: float = 1.0
    cell_size: float = 24.0
    bridge_width: float = 2.0
    density: float = 0.8


@dataclass(slots=True)
class SilhouetteParams:
    threshold: int = 128
    canny_low: int = 80
    canny_high: int = 180
    simplify_tolerance: float = 1.0
