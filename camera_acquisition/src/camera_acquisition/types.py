from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Tuple
import numpy as np


@dataclass(frozen=True)
class FramePacket:
    """Single acquired frame with host timestamps."""

    i: int
    t_before_read_ns: int
    t_after_read_ns: int
    frame: np.ndarray  # BGR image from OpenCV

    @property
    def t_ns(self) -> int:
        """Canonical timestamp: frame available to user-space."""
        return self.t_after_read_ns

    @property
    def t_s(self) -> float:
        return self.t_after_read_ns * 1e-9

    @property
    def read_block_s(self) -> float:
        return (self.t_after_read_ns - self.t_before_read_ns) * 1e-9


@dataclass(frozen=True)
class TrackResult:
    """Tracking output that must preserve the same frame index and timestamp."""

    i: int
    t_ns: int

    # Generic tracked quantity (pick one or populate multiple)
    x: Optional[float] = None
    y: Optional[float] = None
    theta: Optional[float] = None  # radians if you compute angle

    # Quality / diagnostics
    ok: bool = True
    score: Optional[float] = None
    error: Optional[str] = None

    # Optional: allow trackers to attach any extra metadata
    meta: Optional[dict[str, Any]] = None
