from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .types import TrackResult


@dataclass
class TrackCSVLogger:
    path: Path
    _fh: Optional[object] = None
    _w: Optional[csv.writer] = None
    _t_prev_ns: Optional[int] = None

    def __enter__(self) -> "TrackCSVLogger":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("w", newline="", encoding="utf-8")
        self._w = csv.writer(self._fh)
        self._w.writerow(
            ["i", "t_ns", "dt_ns", "x", "y", "theta", "ok", "score", "error"]
        )
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._fh:
            self._fh.close()
        self._fh = None
        self._w = None

    def write(self, r: TrackResult) -> None:
        assert self._w is not None
        dt_ns = ""
        if self._t_prev_ns is not None:
            dt_ns = r.t_ns - self._t_prev_ns
        self._t_prev_ns = r.t_ns

        self._w.writerow(
            [
                r.i,
                r.t_ns,
                dt_ns,
                "" if r.x is None else r.x,
                "" if r.y is None else r.y,
                "" if r.theta is None else r.theta,
                int(bool(r.ok)),
                "" if r.score is None else r.score,
                "" if r.error is None else r.error,
            ]
        )
