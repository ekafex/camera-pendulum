"""
validate_timing.py

Timing validation for camera acquisition.
- Captures frames
- Timestamps frame receipt with time.monotonic_ns()
- Writes timestamps.csv and stats.json
- No image processing, no video writing

Backend: OpenCV (cv2.VideoCapture) for the data plane
Control plane: recommended to run camera_lock_v4l2.py (V4L2 truth)

Usage example:
  python3 scripts/validate_timing.py --dev /dev/video2 --index 2 --duration 60 --out runs/timing_test_60s
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2


@dataclass(frozen=True)
class TimingStats:
    n_frames: int
    duration_s: float
    mean_dt_s: float
    std_dt_s: float
    p01_dt_s: float
    p05_dt_s: float
    p50_dt_s: float
    p95_dt_s: float
    p99_dt_s: float
    achieved_fps: float
    drops_heuristic: int
    drift_s: float


def percentile(sorted_vals: List[float], p: float) -> float:
    # p in [0,100]
    if not sorted_vals:
        return float("nan")
    if p <= 0:
        return sorted_vals[0]
    if p >= 100:
        return sorted_vals[-1]
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if c == f:
        return sorted_vals[f]
    return sorted_vals[f] + (k - f) * (sorted_vals[c] - sorted_vals[f])


def compute_stats(t_ns: List[int], target_fps: float) -> TimingStats:
    n = len(t_ns)
    if n < 2:
        raise ValueError("Need at least 2 frames to compute timing stats.")

    dt_s = [(t_ns[i] - t_ns[i - 1]) * 1e-9 for i in range(1, n)]
    dt_sorted = sorted(dt_s)

    mean_dt = sum(dt_s) / len(dt_s)
    # population std
    var = sum((x - mean_dt) ** 2 for x in dt_s) / len(dt_s)
    std = var**0.5

    T_nom = 1.0 / float(target_fps)
    drops = sum(1 for x in dt_s if x > 1.5 * T_nom)

    drift = (t_ns[-1] - t_ns[0]) * 1e-9 - (n - 1) * T_nom
    achieved_fps = 1.0 / mean_dt

    duration_s = (t_ns[-1] - t_ns[0]) * 1e-9

    return TimingStats(
        n_frames=n,
        duration_s=duration_s,
        mean_dt_s=mean_dt,
        std_dt_s=std,
        p01_dt_s=percentile(dt_sorted, 1),
        p05_dt_s=percentile(dt_sorted, 5),
        p50_dt_s=percentile(dt_sorted, 50),
        p95_dt_s=percentile(dt_sorted, 95),
        p99_dt_s=percentile(dt_sorted, 99),
        achieved_fps=achieved_fps,
        drops_heuristic=drops,
        drift_s=drift,
    )


def run_lock_script(lock_script: Path, dev: str, outdir: Path) -> None:
    # Create a subdir for lock snapshot
    snapdir = outdir / "v4l2_snapshot"
    snapdir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        str(lock_script),
        "--dev",
        dev,
        "--outdir",
        str(snapdir),
        "--width",
        "1280",
        "--height",
        "720",
        "--pixelformat",
        "MJPG",
        "--fps",
        "60",
        "--exposure",
        "157",
        "--gain",
        "0",
        "--wb-temp",
        "4600",
        "--enforce-50hz",
    ]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    (outdir / "camera_lock_stdout.txt").write_text(p.stdout, encoding="utf-8")
    (outdir / "camera_lock_stderr.txt").write_text(p.stderr, encoding="utf-8")
    (outdir / "camera_lock_returncode.txt").write_text(
        str(p.returncode), encoding="utf-8"
    )

    if p.returncode != 0:
        raise RuntimeError(
            "Camera lock script reported failure. See camera_lock_stdout/stderr in run folder."
        )


def open_capture(index: int, width: int, height: int, fps: int) -> cv2.VideoCapture:
    cap = cv2.VideoCapture(index, cv2.CAP_V4L2)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open VideoCapture index={index} with CAP_V4L2.")

    # NOTE: these are requests; V4L2 lock script is the source of truth.
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, float(width))
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, float(height))
    cap.set(cv2.CAP_PROP_FPS, float(fps))

    # Try to prefer MJPG if OpenCV honors it
    fourcc = cv2.VideoWriter_fourcc(*"MJPG")
    cap.set(cv2.CAP_PROP_FOURCC, float(fourcc))

    return cap


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--dev",
        required=True,
        help="V4L2 node, e.g. /dev/video2 (used for v4l2-ctl lock)",
    )
    ap.add_argument(
        "--index",
        type=int,
        required=True,
        help="OpenCV VideoCapture index (usually matches /dev/videoX)",
    )
    ap.add_argument(
        "--duration", type=float, default=60.0, help="Capture duration in seconds"
    )
    ap.add_argument("--target-fps", type=int, default=60)
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--out", required=True, help="Output run directory")
    ap.add_argument(
        "--no-lock", action="store_true", help="Skip running camera_lock_v4l2.py"
    )
    ap.add_argument("--lock-script", default="./camera_lock_v4l2.py")
    args = ap.parse_args()

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    # Save run meta early
    meta = {
        "timestamp_local": datetime.now().isoformat(),
        "platform": {
            "python": sys.version,
            "os": platform.platform(),
            "machine": platform.machine(),
        },
        "capture": {
            "dev": args.dev,
            "index": args.index,
            "width_req": args.width,
            "height_req": args.height,
            "fps_req": args.target_fps,
            "duration_s": args.duration,
            "backend": "opencv_CAP_V4L2",
        },
    }
    (outdir / "run_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    # Lock camera controls + snapshot
    if not args.no_lock:
        lock_script = Path(args.lock_script)
        if not lock_script.exists():
            raise FileNotFoundError(f"Lock script not found: {lock_script}")
        run_lock_script(lock_script, args.dev, outdir)

    # Capture timestamps
    cap = open_capture(args.index, args.width, args.height, args.target_fps)

    t_ns: List[int] = []
    frame_idx: int = 0
    t0 = time.monotonic()
    t_end = t0 + float(args.duration)

    # Warm-up: grab a few frames to settle pipeline
    for _ in range(10):
        cap.read()

    while True:
        now = time.monotonic()
        if now >= t_end:
            break

        ok, _frame = cap.read()
        ts = time.monotonic_ns()
        if not ok:
            # record a gap marker by not appending timestamp; count as a drop-like event later
            continue

        t_ns.append(ts)
        frame_idx += 1

    cap.release()

    # Persist timestamps
    ts_path = outdir / "timestamps.csv"
    with ts_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["frame_index", "t_monotonic_ns"])
        for i, t in enumerate(t_ns):
            w.writerow([i, t])

    if len(t_ns) < 2:
        (outdir / "stats.json").write_text(
            json.dumps(
                {"error": "insufficient_frames", "n_frames": len(t_ns)}, indent=2
            ),
            encoding="utf-8",
        )
        print(f"[FAIL] Captured only {len(t_ns)} frames. See {outdir}")
        return 2

    stats = compute_stats(t_ns, target_fps=float(args.target_fps))
    (outdir / "stats.json").write_text(
        json.dumps(stats.__dict__, indent=2), encoding="utf-8"
    )

    # Print summary
    print(f"Run folder: {outdir}")
    print(f"Frames: {stats.n_frames}  Duration(s): {stats.duration_s:.3f}")
    print(f"Achieved FPS: {stats.achieved_fps:.3f}")
    print(
        f"Δt mean(ms): {stats.mean_dt_s * 1e3:.3f}  std(ms): {stats.std_dt_s * 1e3:.3f}"
    )
    print(
        f"Δt p95(ms): {stats.p95_dt_s * 1e3:.3f}  p99(ms): {stats.p99_dt_s * 1e3:.3f}"
    )
    print(f"Drops (heuristic): {stats.drops_heuristic}")
    print(f"Drift(s): {stats.drift_s:.6f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
