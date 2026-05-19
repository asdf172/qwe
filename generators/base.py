from __future__ import annotations

from abc import ABC, abstractmethod
from shapely.geometry.base import BaseGeometry

from utils.models import CanvasParams, GenerationParams


class BaseGenerator(ABC):
    @abstractmethod
    def generate(self, canvas: CanvasParams, params: GenerationParams) -> BaseGeometry:
        raise NotImplementedError
