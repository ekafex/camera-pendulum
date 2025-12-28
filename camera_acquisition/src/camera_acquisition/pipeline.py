from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Optional

from .acquisition import OpenCVCapture, OpenCVCaptureConfig
from .tracking import Tracker
from .types import FramePacket, TrackResult


@dataclass(frozen=True)
class PipelineConfig:
    duration_s: Optional[float] = None


def run_pipeline(
    cap_cfg: OpenCVCaptureConfig,
    tracker: Tracker,
    pipe_cfg: PipelineConfig = PipelineConfig(),
) -> Iterator[TrackResult]:
    """
    Yields TrackResult with (i, t_ns, measurement) for each successful frame.
    """
    with OpenCVCapture(cap_cfg) as cap:
        for pkt in cap.frames(duration_s=pipe_cfg.duration_s):
            res = tracker.process(pkt)

            # Hard invariant: tracker must preserve frame index and timestamp identity.
            if res.i != pkt.i:
                raise RuntimeError(
                    f"Tracker violated invariant: res.i={res.i} != pkt.i={pkt.i}"
                )
            if res.t_ns != pkt.t_ns:
                raise RuntimeError("Tracker violated invariant: timestamp mismatch")

            yield res
