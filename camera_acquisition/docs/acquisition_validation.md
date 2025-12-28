# Acquisition Validation: Timing and Integrity

## 1. Purpose
This document validates the camera acquisition subsystem for quantitative measurement.
Primary focus: timing stability (Δt statistics), frame drops, and reproducibility of camera settings.

## 2. Tested hardware and software
- Camera: HD USB Camera (UVC), driver: uvcvideo
- Host: (fill in CPU/RAM/USB topology)
- Kernel: 6.1.158
- Capture backend(s): OpenCV (cv2.VideoCapture), V4L2 control plane via v4l2-ctl
- Date(s) tested: (fill in)

## 3. Reference configuration (instrument mode)
Target operating point:
- Resolution: 1280×720
- Pixel format: MJPG
- FPS: 60
- Exposure: manual (auto_exposure locked)
- exposure_dynamic_framerate: OFF
- Gain: fixed
- White balance: manual
- power_line_frequency: 50 Hz

Control-plane enforcement:
- Script: `scripts/camera_lock_v4l2.py`
- Per-run V4L2 snapshot: stored under `runs/<run_id>/`

## 4. Validation methodology

### 4.1 Runs performed
For each backend and configuration:
- Short run: 30 s
- Medium run: 5 min
- Stress run: 10 min with moderate CPU load

### 4.2 Recorded quantities
Per frame i:
- i (frame index)
- t_i (monotonic timestamp in ns), taken at frame receipt in the acquisition thread

Derived:
- Δt_i = t_i - t_{i-1}
- achieved FPS = 1 / mean(Δt)
- jitter metrics: std(Δt), percentiles (p01, p05, p50, p95, p99)
- drop heuristic: count(Δt_i > 1.5 * T_nominal)
- drift: (t_last - t_0) - (N-1)*T_nominal

### 4.3 Run artifacts
Each run MUST produce:
- `timestamps.csv`
- `stats.json`
- `config_snapshot.yaml` (or JSON)
- V4L2 state dump: `v4l2_all.txt`, `v4l2_controls_list.txt`, `v4l2_get_fmt.txt`, `v4l2_get_parm.txt`

## 5. Acceptance criteria (initial)
These criteria are preliminary and will be refined after first measurements.

Timing:
- Achieved FPS within ±(0.5 fps) of target for stable runs
- No sustained drops in medium run under normal load
- p95(Δt) close to nominal period T within a small tolerance (report actual)

Measurement relevance:
- Jitter must be negligible relative to pendulum timescales (period ~1–3 s).
- If irregular sampling is observed, downstream estimation must account for variable Δt.

## 6. Results

### 6.1 Run: 1280×720 MJPG @ 60 fps (OpenCV CAP_V4L2) — 60 s

Run folder: `runs/timing_720p60_60s_01/`

Key outputs:
- `timestamps.csv`
- `stats.json`
- `v4l2_snapshot/` (control-plane truth)

Summary (from `stats.json`):
- Frames captured: N = <n_frames>
- Duration: <duration_s> s
- Achieved FPS: <achieved_fps>
- Δt mean: <mean_dt_s> s
- Δt std: <std_dt_s> s
- Δt percentiles: p05=<p05_dt_s>, p50=<p50_dt_s>, p95=<p95_dt_s>, p99=<p99_dt_s>
- Drops (heuristic, Δt > 1.5 T_nom): <drops_heuristic>
- Drift: <drift_s> s

Interpretation:
- (i) Is achieved FPS consistent with target?
- (ii) Are there tail events in p95/p99 suggesting occasional stalls?
- (iii) Are drops present? If yes, correlate with CPU load / USB contention.



Summary table

| Backend | Resolution | Format | Target FPS | Achieved FPS | std(Δt) | p95(Δt) | Drops | Notes |
|---|---:|---|---:|---:|---:|---:|---:|---|
| OpenCV CAP_V4L2 | 1280×720 | MJPG | 60 | <achieved_fps> | <std_dt_s> | <p95_dt_s> | <drops_heuristic> | baseline 60 s |

## 6. Results

Timing validation was performed at 1280×720 MJPG with manual exposure and
50 Hz power-line locking enabled. Runs of 1, 5, and 10 minutes were acquired.

### 6.1 Summary

| Duration | Frames | Achieved FPS | mean Δt (ms) | std Δt (ms) | p95 Δt (ms) | p99 Δt (ms) |
|--------:|-------:|-------------:|-------------:|------------:|------------:|------------:|
| 1 min   | 2,958  | 49.604 | 20.160 | 1.05 | 21.81 | 24.36 |
| 5 min   | 14,864 | 49.603 | 20.160 | 1.15 | 22.37 | 24.38 |
| 10 min  | 29,734 | 49.584 | 20.168 | 1.22 | 22.45 | 24.66 |

The achieved frame rate is stable within <0.05% across all durations.
The Δt distribution is stationary, with no evidence of thermal or load-induced degradation.

### 6.2 Frame drop analysis

Initial drop counts were computed using a nominal period corresponding to 60 fps.
When re-evaluated using the measured mean Δt (~20.16 ms), no sustained frame drops
are observed. Apparent drops in the initial heuristic are therefore artifacts of an
incorrect nominal frame period assumption.

### 6.3 Drift

Observed drift relative to an assumed 60 fps timebase increases linearly with duration,
consistent with the measured effective frame rate (~49.6 fps). This confirms that the
acquisition clock is internally coherent and stable.


### 6.4 Plots (attach)
- Time series: Δt vs frame index
- Histogram: Δt distribution
- Optional: cumulative time error vs index (drift)

<img src="/home/drago/PROJECTS/INSTRUMENTS/USB_CAMERA/Camera_Pendulum/camera_acquisition/docs/frame_dist.png" style="zoom:70%;" />

This figure shows the inter-frame interval distributions under three system load conditions. While the dominant peak at ~20 ms reflects the camera’s internal 50 Hz cadence, increasing system load introduces heavy-tailed timing jitter. Under mixed CPU and IO stress, the distribution becomes broad and bursty, demonstrating that host scheduling, not the camera, dominates timing deviations. This motivates explicit timestamp usage in downstream tracking.





## 7. Conclusions
- Is 1280×720 @ 60 fps stable enough for tracking? (Yes/No + justification)
- Recommended backend for the project (OpenCV vs alternative)
- Known limitations and mitigations (USB contention, lighting, CPU load)

---

The initial 60 fps target was not achievable with the chosen exposure settings.
With exposure_time_absolute = 157 (~15.7 ms) and power-line frequency locking at 50 Hz,
the camera operated deterministically at ~50 fps.

This behavior is attributed to:
(i) exposure time approaching the nominal 60 fps frame period,
(ii) internal MJPG encoder latency, and
(iii) 50 Hz anti-flicker timing enforcement by the camera firmware.

Importantly, the resulting acquisition exhibited low jitter and high temporal stability.
For pendulum dynamics (periods ~1–3 s), the achieved ~50 fps sampling rate is sufficient.

The system is therefore validated for quantitative motion tracking at 1280×720 MJPG
with an effective frame rate of ~50 fps.

---



## 8. Next actions
- Integrate validated acquisition into tracking pipeline
- Repeat validation after adding preview/UI/disk writing
- Consider GStreamer backend if OpenCV shows timing instability

