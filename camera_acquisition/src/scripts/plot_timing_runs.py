"""
plot_timing_runs.py

Generate timing plots from runs produced by validate_timing.py (updated schema).
Inputs: runs/<run>/timestamps.csv (+ optional stats.json)
Outputs: runs/<run>/plots/*.png

Uses host timestamps:
- default reference: t_after_read_ns
- also plots read blocking time: (t_after_read_ns - t_before_read_ns)
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt


def read_rows(path: Path) -> List[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append(row)
    if not rows:
        raise ValueError(f"No data in {path}")
    return rows


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


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


def ensure_plots_dir(run_dir: Path) -> Path:
    p = run_dir / "plots"
    p.mkdir(parents=True, exist_ok=True)
    return p


def compute_series(rows: List[dict]) -> Tuple[List[float], List[float], List[float]]:
    """
    Returns:
      t_s: time since start (s) for successful frames, based on t_after_read_ns
      dt_s: inter-frame intervals between successive successful frames
      rb_s: read blocking times for successful frames
    """
    ok = [r for r in rows if int(r["read_ok"]) == 1]
    if len(ok) < 2:
        raise ValueError("Need >=2 successful frames for plots")

    t_after = [int(r["t_after_read_ns"]) for r in ok]
    t_before = [int(r["t_before_read_ns"]) for r in ok]

    t0 = t_after[0]
    t_s = [(x - t0) * 1e-9 for x in t_after]
    dt_s = [(t_after[i] - t_after[i - 1]) * 1e-9 for i in range(1, len(t_after))]
    rb_s = [(t_after[i] - t_before[i]) * 1e-9 for i in range(len(t_after))]

    return t_s, dt_s, rb_s


def infer_nominal_period(dt_s: List[float]) -> float:
    xs = sorted(dt_s)
    return xs[len(xs) // 2]


def plot_hist_ms(values_s: List[float], outpath: Path, xlabel: str, title: str, bins: int = 80) -> None:
    plt.figure()
    plt.hist([v * 1e3 for v in values_s], bins=bins)
    plt.xlabel(xlabel)
    plt.ylabel("Count")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(outpath, dpi=160)
    plt.close()


def plot_timeseries(x: List[float], y: List[float], outpath: Path, xlabel: str, ylabel: str, title: str, max_points: int = 20000) -> None:
    plt.figure()
    if len(x) > max_points:
        step = max(1, len(x) // max_points)
        x = x[::step]
        y = y[::step]
    plt.plot(x, y)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(outpath, dpi=160)
    plt.close()


def plot_drift(t_s: List[float], dt_s: List[float], T_nom: float, outpath: Path, title: str) -> None:
    drift = []
    acc = 0.0
    for k, d in enumerate(dt_s, start=1):
        acc += d
        drift.append(acc - k * T_nom)
    x = t_s[1:]
    plot_timeseries(
        x[:len(drift)],
        drift,
        outpath,
        xlabel="Time since start (s)",
        ylabel="Cumulative drift (s)",
        title=title,
        max_points=20000,
    )


def plot_drops(t_s: List[float], dt_s: List[float], threshold_s: float, outpath: Path) -> None:
    # events where dt_s[i] > threshold, associate to time t_s[i+1]
    xs = []
    ys = []
    for i, d in enumerate(dt_s):
        if d > threshold_s:
            xs.append(t_s[i + 1])
            ys.append(d * 1e3)  # ms

    plt.figure()
    if xs:
        plt.plot(xs, ys, marker="o", linestyle="none")
    plt.xlabel("Time since start (s)")
    plt.ylabel("Flagged Δt (ms)")
    plt.title(f"Flagged long-Δt events (Δt > {threshold_s*1e3:.2f} ms)")
    plt.tight_layout()
    plt.savefig(outpath, dpi=160)
    plt.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True, help="Run directories containing timestamps.csv")
    ap.add_argument("--requested-fps", type=float, default=None, help="Requested fps for drift-vs-requested plot (optional)")
    ap.add_argument("--drop-k", type=float, default=1.5, help="Drop threshold multiplier: threshold = k*T_nom")
    args = ap.parse_args()

    for run in args.runs:
        run_dir = Path(run)
        ts_path = run_dir / "timestamps.csv"
        if not ts_path.exists():
            raise FileNotFoundError(f"Missing {ts_path}")

        rows = read_rows(ts_path)
        stats = load_json(run_dir / "stats.json")

        t_s, dt_s, rb_s = compute_series(rows)
        T_inf = infer_nominal_period(dt_s)
        fps_inf = 1.0 / T_inf
        threshold = args.drop_k * T_inf

        plots_dir = ensure_plots_dir(run_dir)

        # Δt plots
        plot_hist_ms(dt_s, plots_dir / "dt_hist.png", xlabel="Δt (ms)", title="Inter-frame interval distribution Δt")
        plot_timeseries(
            list(range(len(dt_s))),
            [d * 1e3 for d in dt_s],
            plots_dir / "dt_timeseries.png",
            xlabel="Interval index",
            ylabel="Δt (ms)",
            title="Δt vs index",
        )

        # Read blocking time plots
        plot_hist_ms(rb_s, plots_dir / "read_block_hist.png", xlabel="Read block time (ms)", title="cap.read() blocking time distribution")
        plot_timeseries(
            t_s,
            [v * 1e3 for v in rb_s],
            plots_dir / "read_block_timeseries.png",
            xlabel="Time since start (s)",
            ylabel="Read block time (ms)",
            title="Read block time vs time",
        )

        # Drift plots
        plot_drift(t_s, dt_s, T_inf, plots_dir / "drift_vs_inferred.png", title=f"Drift vs inferred nominal (fps≈{fps_inf:.3f})")

        if args.requested_fps and args.requested_fps > 0:
            T_req = 1.0 / args.requested_fps
            plot_drift(t_s, dt_s, T_req, plots_dir / "drift_vs_requested.png", title=f"Drift vs requested ({args.requested_fps:.1f} fps)")

        # Drops timeline (relative to inferred nominal)
        plot_drops(t_s, dt_s, threshold, plots_dir / "drops_timeseries.png")

        # Write a small plot summary
        summary = {
            "inferred_nominal_period_s": T_inf,
            "inferred_fps": fps_inf,
            "drop_threshold_s": threshold,
            "n_success_frames": len(t_s),
            "n_intervals": len(dt_s),
            "stats_json_present": bool(stats),
        }
        (plots_dir / "plot_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

        print(f"[OK] Wrote plots to {plots_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

