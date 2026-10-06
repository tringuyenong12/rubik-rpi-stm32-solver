from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

import numpy as np


@dataclass(frozen=True)
class ColorSample:
    label: str
    lab: tuple[float, float, float]


class NearestCenterColorClassifier:
    """Classify sticker colors by nearest calibrated center in LAB color space."""

    def __init__(self, centers: list[ColorSample]) -> None:
        labels = {sample.label for sample in centers}
        if labels != set("URFDLB"):
            raise ValueError("Expected exactly one center sample for each URFDLB face")
        self.centers = centers

    def classify_lab(self, lab: tuple[float, float, float]) -> str:
        return min(self.centers, key=lambda sample: _distance(sample.lab, lab)).label

    def classify_grid(self, lab_grid: list[tuple[float, float, float]]) -> str:
        if len(lab_grid) != 54:
            raise ValueError(f"Expected 54 samples, got {len(lab_grid)}")
        return "".join(self.classify_lab(sample) for sample in lab_grid)


def mean_lab_from_bgr_patch(patch: np.ndarray) -> tuple[float, float, float]:
    if patch.size == 0:
        raise ValueError("Patch is empty")
    lab = _bgr_to_lab(patch)
    mean = lab.reshape(-1, 3).mean(axis=0)
    return float(mean[0]), float(mean[1]), float(mean[2])


def _bgr_to_lab(image: np.ndarray) -> np.ndarray:
    import cv2

    return cv2.cvtColor(image, cv2.COLOR_BGR2LAB)


def _distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))

