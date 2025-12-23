"""
camera_lock_v4l2.py

Instrument-grade camera configuration and verification via v4l2-ctl.

Design intent:
- Use v4l2-ctl as the source of truth (kernel driver state)
- Apply a deterministic configuration (format, fps, exposure, gain, WB)
- Verify after setting
- Save a reproducibility snapshot (v4l2-ctl outputs)

Requirements:
- Linux + v4l2-ctl (package: v4l-utils)
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class CameraConfig:
    width: int = 1280
    height: int = 720
    pixelformat: str = "MJPG"  # must match v4l2 fourcc, e.g. MJPG, YUYV
    fps: int = 60

    # Exposure controls (UVC typical)
    auto_exposure: int = (
        1  # NOTE: on many UVC cams, 1 == manual. Verify via `v4l2-ctl -l`.
    )
    exposure_time_absolute: int = 157
    exposure_dynamic_framerate: int = 0  # 0 = disable dynamic framerate

    # Image controls
    gain: int = 0
    white_balance_automatic: int = 0
    white_balance_temperature: int = 4600

    # Optional: keep as-is unless you want to enforce
    power_line_frequency: Optional[int] = None  # e.g. 1 for 50Hz on many cams


def _run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=check,
    )


def require_v4l2_ctl() -> None:
    if shutil.which("v4l2-ctl") is None:
        raise RuntimeError(
            "v4l2-ctl not found. Install v4l-utils.\n"
            "Debian/Ubuntu: sudo apt install v4l-utils"
        )


def v4l2_ctl(dev: str, *args: str, check: bool = True) -> str:
    cmd = ["v4l2-ctl", "-d", dev, *args]
    p = _run(cmd, check=check)
    if p.returncode != 0 and not check:
        return (p.stdout or "") + (p.stderr or "")
    return p.stdout


def set_format_and_fps(dev: str, cfg: CameraConfig) -> None:
    v4l2_ctl(
        dev,
        f"--set-fmt-video=width={cfg.width},height={cfg.height},pixelformat={cfg.pixelformat}",
    )
    v4l2_ctl(dev, f"--set-parm={cfg.fps}")


def set_controls(dev: str, cfg: CameraConfig) -> None:
    # Apply in a sequence that ensures inactive controls become active.
    # 1) Exposure mode first, then exposure time.
    v4l2_ctl(dev, "-c", f"auto_exposure={cfg.auto_exposure}")
    v4l2_ctl(dev, "-c", f"exposure_dynamic_framerate={cfg.exposure_dynamic_framerate}")

    # exposure_time_absolute may fail if still inactive; we verify later.
    v4l2_ctl(dev, "-c", f"exposure_time_absolute={cfg.exposure_time_absolute}")

    # 2) Gain, WB
    v4l2_ctl(dev, "-c", f"gain={cfg.gain}")
    v4l2_ctl(dev, "-c", f"white_balance_automatic={cfg.white_balance_automatic}")
    # WB temp is often inactive if auto WB is on; we force auto WB off above.
    v4l2_ctl(dev, "-c", f"white_balance_temperature={cfg.white_balance_temperature}")

    # Optional power line frequency enforcement
    if cfg.power_line_frequency is not None:
        v4l2_ctl(dev, "-c", f"power_line_frequency={cfg.power_line_frequency}")


def parse_get_fmt(output: str) -> Dict[str, str]:
    # Example lines commonly include:
    #   Width/Height      : 1280/720
    #   Pixel Format      : 'MJPG'
    d: Dict[str, str] = {}
    m = re.search(r"Width/Height\s*:\s*(\d+)\s*/\s*(\d+)", output)
    if m:
        d["width"] = m.group(1)
        d["height"] = m.group(2)
    m = re.search(r"Pixel Format\s*:\s*'([A-Z0-9]{4})'", output)
    if m:
        d["pixelformat"] = m.group(1)
    return d


def parse_get_parm(output: str) -> Dict[str, str]:
    # Typically contains:
    #   Frames per second: 60.000 (60/1)
    d: Dict[str, str] = {}
    m = re.search(r"Frames per second\s*:\s*([0-9.]+)", output)
    if m:
        d["fps"] = m.group(1)
    return d


def get_control_value(dev: str, name: str) -> Optional[str]:
    # v4l2-ctl -C control prints: "<name>: <value>" or "<name>: <value> (<label>)"
    out = v4l2_ctl(dev, "-C", name, check=False).strip()

    if "Unknown control" in out or "unknown control" in out or "VIDIOC_G_CTRL" in out:
        return None

    parts = out.split(":", 1)
    if len(parts) != 2:
        return None

    raw = parts[1].strip()

    # Normalize "1 (Manual Mode)" -> "1"
    m = re.match(r"^(-?\d+)\s*(?:\(.+\))?$", raw)
    if m:
        return m.group(1)

    # Normalize "50 Hz" style menu labels if any appear (rare in -C, more common elsewhere)
    return raw



def verify(dev: str, cfg: CameraConfig) -> Tuple[bool, str]:
    ok = True
    lines = []

    fmt_out = v4l2_ctl(dev, "--get-fmt-video")
    fmt = parse_get_fmt(fmt_out)

    parm_out = v4l2_ctl(dev, "--get-parm")
    parm = parse_get_parm(parm_out)

    def chk(label: str, expected: str, actual: Optional[str]) -> None:
        nonlocal ok
        if actual is None:
            ok = False
            lines.append(f"[FAIL] {label}: expected {expected}, actual <unavailable>")
            return
        if actual != expected:
            ok = False
            lines.append(f"[FAIL] {label}: expected {expected}, actual {actual}")
        else:
            lines.append(f"[ OK ] {label}: {actual}")

    # Format checks
    chk("width", str(cfg.width), fmt.get("width"))
    chk("height", str(cfg.height), fmt.get("height"))
    chk("pixelformat", cfg.pixelformat, fmt.get("pixelformat"))

    # FPS check: allow slight float representation differences (e.g. 60.000)
    fps_actual = parm.get("fps")
    if fps_actual is None:
        ok = False
        lines.append(f"[FAIL] fps: expected {cfg.fps}, actual <unavailable>")
    else:
        try:
            fa = float(fps_actual)
            if abs(fa - float(cfg.fps)) > 0.5:
                ok = False
                lines.append(f"[FAIL] fps: expected {cfg.fps}, actual {fa}")
            else:
                lines.append(f"[ OK ] fps: {fa:.3f}")
        except ValueError:
            ok = False
            lines.append(f"[FAIL] fps: expected {cfg.fps}, actual {fps_actual}")

    # Control checks (best effort; some drivers report differently)
    ctrl_map = {
        "auto_exposure": str(cfg.auto_exposure),
        "exposure_dynamic_framerate": str(cfg.exposure_dynamic_framerate),
        "exposure_time_absolute": str(cfg.exposure_time_absolute),
        "gain": str(cfg.gain),
        "white_balance_automatic": str(cfg.white_balance_automatic),
        "white_balance_temperature": str(cfg.white_balance_temperature),
    }
    if cfg.power_line_frequency is not None:
        ctrl_map["power_line_frequency"] = str(cfg.power_line_frequency)

    for k, exp in ctrl_map.items():
        act = get_control_value(dev, k)
        chk(k, exp, act)

    return ok, "\n".join(lines)


def snapshot(dev: str, outdir: Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)

    def dump(name: str, *args: str) -> None:
        text = v4l2_ctl(dev, *args, check=False)
        (outdir / name).write_text(text, encoding="utf-8")

    dump("v4l2_info.txt", "--info")
    dump("v4l2_all.txt", "--all")
    dump("v4l2_controls_list.txt", "-l")
    dump("v4l2_formats_ext.txt", "--list-formats-ext")
    dump("v4l2_get_fmt.txt", "--get-fmt-video")
    dump("v4l2_get_parm.txt", "--get-parm")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", required=True, help="V4L2 device node, e.g. /dev/video2")
    ap.add_argument(
        "--outdir", default=None, help="Directory to write snapshot outputs"
    )
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--pixelformat", default="MJPG")
    ap.add_argument("--fps", type=int, default=60)
    ap.add_argument("--exposure", type=int, default=157, help="exposure_time_absolute")
    ap.add_argument("--gain", type=int, default=0)
    ap.add_argument("--wb-temp", type=int, default=4600)
    ap.add_argument(
        "--enforce-50hz",
        action="store_true",
        help="Set power_line_frequency to 50 Hz if available",
    )
    args = ap.parse_args()

    require_v4l2_ctl()

    cfg = CameraConfig(
        width=args.width,
        height=args.height,
        pixelformat=args.pixelformat,
        fps=args.fps,
        exposure_time_absolute=args.exposure,
        gain=args.gain,
        white_balance_temperature=args.wb_temp,
        power_line_frequency=(1 if args.enforce_50hz else None),
    )

    # Apply config
    set_format_and_fps(args.dev, cfg)
    set_controls(args.dev, cfg)

    # Verify
    ok, report = verify(args.dev, cfg)
    print(report)

    # Snapshot
    if args.outdir:
        outdir = Path(args.outdir)
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        outdir = Path("runs") / f"camera_lock_{ts}"
    snapshot(args.dev, outdir)
    print(f"\nSaved V4L2 snapshot to: {outdir}")

    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
