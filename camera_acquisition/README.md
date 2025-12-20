# Camera & Acquisition Module

## 1. Scope and objective
This module provides deterministic image acquisition from a USB camera for quantitative measurement (e.g., pendulum tracking). It is treated as an instrument subsystem: it must produce raw frames, timestamps, and metadata with known performance characteristics.

**In scope**
- Camera enumeration and parameter control (resolution, FPS target, exposure, gain, pixel format where possible)
- Frame acquisition with monotonic timestamps and bounded buffering
- Metadata capture and run logging
- Validation utilities focused on timing stability and frame integrity

**Out of scope**
- Tracking / computer vision algorithms
- Camera calibration (intrinsics/extrinsics)
- Physical parameter estimation (e.g., angle, length, g)
- Uncertainty propagation beyond acquisition-level metrics

## 2. Outputs (contract)
Each acquisition run MUST be able to produce:
- **Raw frames** (unmodified by processing; optional encoding for storage is allowed but must be documented)
- **Per-frame timestamp** from a monotonic clock (exposure time is not assumed unless supported)
- **Per-run metadata**: camera ID, negotiated settings, actual settings, host info, software version
- **Diagnostics**: achieved FPS, inter-frame interval distribution, dropped frames count, buffer overflows

These artifacts are required for later calibration, validation, and uncertainty analysis.

## 3. Timing model (principles)
This project distinguishes:
- **Exposure time** (when photons hit sensor) — generally unknown without hardware timestamps
- **Frame delivery time** (when a frame becomes available to software)
- **Timestamp time** (when the acquisition code stamps the frame)

Default assumption (unless camera provides hardware timestamps):
- Frames are timestamped using an OS monotonic clock at the moment they are received by the acquisition thread.
- Latency from exposure to delivery is not zero and is treated as an unknown bias unless characterized.

The timing validation experiment (Section 7) quantifies jitter, drops, and drift of the acquisition timestamps.

## 4. Repository structure
Suggested layout:

```toml
camera_acquisition/
  README.md
  docs/
    camera_hardware.md
    timing_model.md
    acquisition_validation.md
  config/
    camera_default.yaml
  src/
    camera/
      backend.py          # OpenCV/V4L2 wrapper; no business logic
      camera_device.py    # device control, capability query
    acquisition/
      frame_grabber.py    # grab -> timestamp -> enqueue
      timestamping.py     # monotonic clock utilities
      buffer.py           # bounded queue/ring buffer
    io/
      writer.py           # optional frame writer (raw/encoded)
      metadata.py         # run metadata schema + serialization
  scripts/
    acquire_preview.py    # bring-up: preview + live stats
    acquire_run.py        # produce a "run folder" with data+metadata
    validate_timing.py    # timing validation experiment runner
  tests/
    test_timing_basic.py
    test_buffer_overflow.py
```



## 5. Configuration

All tunable parameters must be configuration-driven (no hidden constants).

Minimum required config keys:
- camera selection: device index / serial / VID:PID (best-effort)
- resolution: width, height
- target_fps
- pixel_format (if supported)
- exposure: auto/manual, exposure value (if supported)
- gain: auto/manual, gain value (if supported)
- white_balance: auto/manual (if supported)
- run settings: duration_s, output_dir, write_frames true/false, encoding

Config snapshot MUST be stored alongside each run.

## 6. Design rules (non-negotiable)
1. **Single responsibility acquisition thread**:
   - Grab frame -> timestamp -> enqueue
   - No processing, no disk IO, no UI work inside the grab loop.
2. **Bounded buffering**:
   - The buffer must be finite and overflow behavior must be explicit (drop newest/oldest + count drops).
3. **Reproducibility**:
   - Every run writes metadata + config snapshot + git commit hash (if available).
4. **Observability**:
   - Every run reports achieved FPS, drop rate, and inter-frame interval statistics.

## 7. Timing validation experiment (must pass before tracking)
Goal: quantify whether the acquisition provides time series suitable for motion measurement.

Primary metrics:
- Inter-frame interval: Δt_i = t_i - t_{i-1}
- Achieved FPS = 1 / mean(Δt)
- Jitter: std(Δt) and robust percentiles (e.g., 5th/95th)
- Drop detection: missed intervals relative to nominal period
- Drift: deviation of cumulative time from nominal over the run duration

Required experiment outputs:
- run folder with:
  - timestamps.csv (frame_index, t_monotonic_ns, optional t_wallclock)
  - stats.json (summary metrics)
  - config_snapshot.yaml
  - optional sample frames (first/last/periodic) for sanity checks

Acceptance criteria (initial; refine after first measurements):
- No sustained frame drops under normal CPU load for a 5–10 minute run
- Jitter small compared with the system dynamics (pendulum typical periods ~1–3 s):
  - as a starting point: std(Δt) << 1% of the pendulum period
- Achieved FPS within a tolerable band of the target (define per mode/resolution)

## 8. How this integrates with the full pipeline
Downstream modules will assume:
- A time-ordered frame stream with monotonic timestamps
- Known acquisition performance (jitter/drops quantified)
- A stable configuration record per run

The tracking module must treat acquisition timestamps as ground truth for sampling times unless a superior hardware timestamp is later introduced.

## 9. Operating modes (planned)
- Bring-up preview: verify camera selection and controls, show live stats (no disk writes)
- Data run: produce run folder, optionally write frames or a video stream
- Validation run: collect timestamps and compute timing stats

## 10. License and attribution
This module is part of the Camera_Calib / Pendulum measurement pipeline project.
Add licenses/attribution here as the repository matures.

