from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Optional, Tuple

import cv2
import numpy as np

from .types import FramePacket, TrackResult


class Tracker(Protocol):
    def process(self, pkt: FramePacket) -> TrackResult: ...


@dataclass(frozen=True)
class DummyCentroidTrackerConfig:
    # This is a placeholder. You will replace with your real tracking logic.
    blur_ksize: int = 5
    threshold: int = 200  # for bright marker, for example
    min_area: int = 50


class DummyCentroidTracker:
    """
    Minimal example tracker:
    - converts to grayscale
    - thresholds for bright blob
    - computes centroid of largest contour

    This is NOT the final tracker; it exists to validate the pipeline and dt handling.
    """

    def __init__(self, cfg: DummyCentroidTrackerConfig = DummyCentroidTrackerConfig()):
        self.cfg = cfg

    def process(self, pkt: FramePacket) -> TrackResult:
        try:
            gray = cv2.cvtColor(pkt.frame, cv2.COLOR_BGR2GRAY)
            if self.cfg.blur_ksize > 0:
                gray = cv2.GaussianBlur(
                    gray, (self.cfg.blur_ksize, self.cfg.blur_ksize), 0
                )

            _, bw = cv2.threshold(gray, self.cfg.threshold, 255, cv2.THRESH_BINARY)
            contours, _hier = cv2.findContours(
                bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            if not contours:
                return TrackResult(
                    i=pkt.i, t_ns=pkt.t_ns, ok=False, error="no_contours"
                )

            # largest contour
            c = max(contours, key=cv2.contourArea)
            area = float(cv2.contourArea(c))
            if area < self.cfg.min_area:
                return TrackResult(
                    i=pkt.i,
                    t_ns=pkt.t_ns,
                    ok=False,
                    error="contour_too_small",
                    score=area,
                )

            m = cv2.moments(c)
            if m["m00"] == 0:
                return TrackResult(
                    i=pkt.i, t_ns=pkt.t_ns, ok=False, error="zero_moment"
                )

            x = float(m["m10"] / m["m00"])
            y = float(m["m01"] / m["m00"])

            return TrackResult(i=pkt.i, t_ns=pkt.t_ns, x=x, y=y, ok=True, score=area)

        except Exception as e:
            return TrackResult(
                i=pkt.i,
                t_ns=pkt.t_ns,
                ok=False,
                error=f"exception:{type(e).__name__}:{e}",
            )
