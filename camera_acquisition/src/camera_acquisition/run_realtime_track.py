#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from camera_acquisition.acquisition import OpenCVCaptureConfig
from camera_acquisition.logging import TrackCSVLogger
from camera_acquisition.pipeline import PipelineConfig, run_pipeline
from camera_acquisition.tracking import DummyCentroidTracker, DummyCentroidTrackerConfig


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", type=int, required=True)
    ap.add_argument("--duration", type=float, default=30.0)
    ap.add_argument("--out", required=True, help="CSV output path")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--requested-fps", type=int, default=60)
    args = ap.parse_args()

    cap_cfg = OpenCVCaptureConfig(
        index=args.index,
        width=args.width,
        height=args.height,
        requested_fps=args.requested_fps,
        warmup_frames=30,
    )

    tracker = DummyCentroidTracker(DummyCentroidTrackerConfig())

    pipe_cfg = PipelineConfig(duration_s=args.duration)

    out_path = Path(args.out)
    with TrackCSVLogger(out_path) as logger:
        for r in run_pipeline(cap_cfg, tracker, pipe_cfg):
            logger.write(r)

    print(f"[OK] wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
