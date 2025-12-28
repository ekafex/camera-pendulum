from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterator, Optional

import cv2

from .types import FramePacket


@dataclass(frozen=True)
class OpenCVCaptureConfig:
    index: int
    width: int = 1280
    height: int = 720
    requested_fps: int = 60
    fourcc: str = "MJPG"  # request only; control plane via v4l2 is authoritative
    warmup_frames: int = 30


class OpenCVCapture:
    """
    Acquisition source: yields FramePacket objects with host timestamps.

    Notes:
    - Timestamps are host monotonic ns around cap.read().
    - This module does not set V4L2 controls; do that separately (camera_lock_v4l2.py).
    """

    def __init__(self, cfg: OpenCVCaptureConfig):
        self.cfg = cfg
        self.cap: Optional[cv2.VideoCapture] = None

    def __enter__(self) -> "OpenCVCapture":
        cap = cv2.VideoCapture(self.cfg.index, cv2.CAP_V4L2)
        if not cap.isOpened():
            raise RuntimeError(
                f"Could not open camera index={self.cfg.index} with CAP_V4L2"
            )

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, float(self.cfg.width))
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, float(self.cfg.height))
        cap.set(cv2.CAP_PROP_FPS, float(self.cfg.requested_fps))
        cap.set(cv2.CAP_PROP_FOURCC, float(cv2.VideoWriter_fourcc(*self.cfg.fourcc)))

        # Warm-up
        for _ in range(max(0, self.cfg.warmup_frames)):
            cap.read()

        self.cap = cap
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.cap is not None:
            self.cap.release()
        self.cap = None

    def frames(self, duration_s: Optional[float] = None) -> Iterator[FramePacket]:
        """
        Iterate frames until duration_s expires (if set) else infinite.
        """
        if self.cap is None:
            raise RuntimeError("OpenCVCapture must be used as a context manager")

        t_end = None if duration_s is None else (time.monotonic() + float(duration_s))
        i = 0

        while True:
            if t_end is not None and time.monotonic() >= t_end:
                break

            t_before = time.monotonic_ns()
            ok, frame = self.cap.read()
            t_after = time.monotonic_ns()

            if not ok:
                # In this design, we skip failed reads rather than yielding invalid packets.
                # If you prefer, yield a packet with ok flag; but then TrackResult needs to mirror that.
                continue

            yield FramePacket(
                i=i, t_before_read_ns=t_before, t_after_read_ns=t_after, frame=frame
            )
            i += 1
