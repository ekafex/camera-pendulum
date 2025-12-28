"""
validate_timing.py

Timing validation for camera acquisition.
- Captures frames with OpenCV (CAP_V4L2)
- Records host monotonic timestamps:
    t_before_read_ns: taken immediately before cap.read()
    t_after_read_ns : taken immediately after cap.read()
  The primary "frame receive time" is t_after_read_ns.
- Writes:
    timestamps.csv
    stats.json
    run_meta.json
    (optional) v4l2 snapshot via camera_lock_v4l2.py

Important:
- These are HOST-assigned timestamps, not camera exposure timestamps.
- t_after_read_ns includes blocking/latency effects; validated via Δt statistics.
"""

from __future__ import annotations

import argparse
import csv
import json
import platform
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import cv2


@dataclass(frozen=True)
class SeriesStats:
    n: int
    mean: float
    std: float
    p01: float
    p05: float
    p50: float
    p95: float
    p99: float
    min: float
    max: float


@dataclass(frozen=True)
class TimingStats:
    n_frames_ok: int
    n_read_fail: int
    duration_s: float

    requested_fps: float
    inferred_fps: float

    dt_s: SeriesStats                # Δt based on t_after_read
    read_block_s: SeriesStats        # (t_after - t_before) for successful reads

    drops_inferred_nominal: int      # Δt > 1.5*T_inferred
    drops_requested_nominal: int     # Δt > 1.5*T_requested

    drift_vs_requested_s: float      # (t_last-t_0) - (N-1)*T_requested
    drift_vs_inferred_s: float       # (t_last-t_0) - (N-1)*T_inferred


def percentile(sorted_vals: List[float], p: float) -> float:
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


def compute_series_stats(x: List[float]) -> SeriesStats:
    if not x:
        raise ValueError("Empty series")
    n = len(x)
    mean = sum(x) / n
    var = sum((v - mean) ** 2 for v in x) / n  # population variance
    std = var ** 0.5
    xs = sorted(x)
    return SeriesStats(
        n=n,
        mean=mean,
        std=std,
        p01=percentile(xs, 1),
        p05=percentile(xs, 5),
        p50=percentile(xs, 50),
        p95=percentile(xs, 95),
        p99=percentile(xs, 99),
        min=xs[0],
        max=xs[-1],
    )


def infer_nominal_period(dt_s: List[float]) -> float:
    # robust nominal period: median Δt
    xs = sorted(dt_s)
    return xs[len(xs) // 2]


def run_lock_script(lock_script: Path, dev: str, outdir: Path) -> None:
    snapdir = outdir / "v4l2_snapshot"
    snapdir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        str(lock_script),
        "--dev", dev,
        "--outdir", str(snapdir),
        "--width", "1280",
        "--height", "720",
        "--pixelformat", "MJPG",
        "--fps", "60",
        "--exposure", "157",
        "--gain", "0",
        "--wb-temp", "4600",
        "--enforce-50hz",
    ]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    (outdir / "camera_lock_stdout.txt").write_text(p.stdout, encoding="utf-8")
    (outdir / "camera_lock_stderr.txt").write_text(p.stderr, encoding="utf-8")
    (outdir / "camera_lock_returncode.txt").write_text(str(p.returncode), encoding="utf-8")

    if p.returncode != 0:
        raise RuntimeError(
            "Camera lock script reported failure. Inspect camera_lock_stdout/stderr in the run folder."
        )


def open_capture(index: int, width: int, height: int, fps: int) -> cv2.VideoCapture:
    cap = cv2.VideoCapture(index, cv2.CAP_V4L2)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open VideoCapture index={index} with CAP_V4L2.")

    # Requests only (control plane is V4L2 via lock script)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, float(width))
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, float(height))
    cap.set(cv2.CAP_PROP_FPS, float(fps))

    # Request MJPG
    fourcc = cv2.VideoWriter_fourcc(*"MJPG")
    cap.set(cv2.CAP_PROP_FOURCC, float(fourcc))

    return cap


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", required=True, help="V4L2 node, e.g. /dev/video2 (for v4l2-ctl lock)")
    ap.add_argument("--index", type=int, required=True, help="OpenCV VideoCapture index (usually matches /dev/videoX)")
    ap.add_argument("--duration", type=float, default=60.0, help="Capture duration in seconds")
    ap.add_argument("--requested-fps", type=float, default=60.0, help="Requested FPS (used for diagnostics/drift)")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--out", required=True, help="Output run directory")
    ap.add_argument("--no-lock", action="store_true", help="Skip running camera_lock_v4l2.py")
    ap.add_argument("--lock-script", default="scripts/camera_lock_v4l2.py")
    ap.add_argument("--warmup-frames", type=int, default=10, help="Warm-up read count before measurement")
    args = ap.parse_args()

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

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
            "fps_req": args.requested_fps,
            "duration_s": args.duration,
            "backend": "opencv_CAP_V4L2",
            "timestamp_origin": "host_monotonic_ns",
            "timestamp_definition": {
                "t_before_read_ns": "monotonic_ns immediately before cap.read()",
                "t_after_read_ns": "monotonic_ns immediately after cap.read() (primary receive timestamp)",
            },
        },
    }
    (outdir / "run_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    if not args.no_lock:
        lock_script = Path(args.lock_script)
        if not lock_script.exists():
            raise FileNotFoundError(f"Lock script not found: {lock_script}")
        run_lock_script(lock_script, args.dev, outdir)

    cap = open_capture(args.index, args.width, args.height, int(round(args.requested_fps)))

    # Warm-up
    for _ in range(max(0, args.warmup_frames)):
        cap.read()

    rows = []  # each row: (i, ok, t_before_ns, t_after_ns)
    n_fail = 0

    t_start = time.monotonic()
    t_end = t_start + float(args.duration)

    i = 0
    while True:
        now = time.monotonic()
        if now >= t_end:
            break

        t_before = time.monotonic_ns()
        ok, _frame = cap.read()
        t_after = time.monotonic_ns()

        if not ok:
            n_fail += 1
        rows.append((i, ok, t_before, t_after))
        i += 1

    cap.release()

    # Write timestamps.csv
    ts_path = outdir / "timestamps.csv"
    with ts_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["# frame_index", "read_ok", "t_before_read_ns", "t_after_read_ns"])
        for r in rows:
            w.writerow([r[0], int(bool(r[1])), r[2], r[3]])

    # Extract successful timestamps for dt analysis
    t_after_ok = [r[3] for r in rows if r[1]]
    read_block_s = [(r[3] - r[2]) * 1e-9 for r in rows if r[1]]

    if len(t_after_ok) < 2:
        (outdir / "stats.json").write_text(
            json.dumps({"error": "insufficient_frames", "n_frames_ok": len(t_after_ok), "n_read_fail": n_fail}, indent=2),
            encoding="utf-8",
        )
        print(f"[FAIL] Captured only {len(t_after_ok)} successful frames. See {outdir}")
        return 2

    # dt series based on after-read timestamps
    dt_s = [(t_after_ok[k] - t_after_ok[k - 1]) * 1e-9 for k in range(1, len(t_after_ok))]
    dt_stats = compute_series_stats(dt_s)
    rb_stats = compute_series_stats(read_block_s)

    T_inferred = infer_nominal_period(dt_s)
    fps_inferred = 1.0 / T_inferred

    T_req = 1.0 / float(args.requested_fps)

    drops_inf = sum(1 for d in dt_s if d > 1.5 * T_inferred)
    drops_req = sum(1 for d in dt_s if d > 1.5 * T_req)

    duration_s = (t_after_ok[-1] - t_after_ok[0]) * 1e-9
    n_ok = len(t_after_ok)

    drift_req = duration_s - (n_ok - 1) * T_req
    drift_inf = duration_s - (n_ok - 1) * T_inferred

    stats = TimingStats(
        n_frames_ok=n_ok,
        n_read_fail=n_fail,
        duration_s=duration_s,
        requested_fps=float(args.requested_fps),
        inferred_fps=fps_inferred,
        dt_s=dt_stats,
        read_block_s=rb_stats,
        drops_inferred_nominal=drops_inf,
        drops_requested_nominal=drops_req,
        drift_vs_requested_s=drift_req,
        drift_vs_inferred_s=drift_inf,
    )

    (outdir / "stats.json").write_text(json.dumps(asdict(stats), indent=2), encoding="utf-8")

    # Console summary
    print(f"Run folder: {outdir}")
    print(f"Frames OK: {stats.n_frames_ok}   Read failures: {stats.n_read_fail}")
    print(f"Duration(s): {stats.duration_s:.3f}")
    print(f"Requested FPS: {stats.requested_fps:.3f}   Inferred FPS: {stats.inferred_fps:.3f}")
    print(f"Δt mean(ms): {stats.dt_s.mean*1e3:.3f}  std(ms): {stats.dt_s.std*1e3:.3f}  p95(ms): {stats.dt_s.p95*1e3:.3f}  p99(ms): {stats.dt_s.p99*1e3:.3f}")
    print(f"Read block mean(ms): {stats.read_block_s.mean*1e3:.3f}  p95(ms): {stats.read_block_s.p95*1e3:.3f}  p99(ms): {stats.read_block_s.p99*1e3:.3f}")
    print(f"Drops (inferred nominal): {stats.drops_inferred_nominal}   Drops (requested nominal): {stats.drops_requested_nominal}")
    print(f"Drift vs requested(s): {stats.drift_vs_requested_s:.6f}   Drift vs inferred(s): {stats.drift_vs_inferred_s:.6f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

