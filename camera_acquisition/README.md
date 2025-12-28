

# Camera Acquisition Validation and Timing Characterization

## 1. Purpose and scope

This document validates the camera acquisition subsystem used in the pendulum
measurement pipeline. The objective is to characterize frame timing behavior,
identify sources of jitter and drift, and determine whether the acquisition
layer is suitable for quantitative motion tracking.

The validation focuses exclusively on:

- frame arrival timing,
- timestamp origin and interpretation,
- stability under system load.

Image processing, tracking, and physical parameter extraction are explicitly
out of scope.

---

## 2. Hardware and software context

- Camera: USB UVC camera (HD USB Camera)
- Driver: `uvcvideo`
- Host OS: Linux
- Capture backend: OpenCV (`cv2.VideoCapture`) with V4L2 backend
- Control plane: V4L2 (`v4l2-ctl`)
- Pixel format: MJPG
- Resolution: 1280 × 720

The camera is configured with:

- manual exposure,
- fixed gain,
- dynamic framerate disabled,
- power-line frequency set to 50 Hz.

---

## 3. Timestamp model

### 3.1 Timestamp origin

All frame timestamps are assigned **on the host**, not by the camera firmware.

For each frame, two host timestamps are recorded:

- `t_before_read_ns`: taken immediately before calling `cap.read()`
- `t_after_read_ns`: taken immediately after `cap.read()` returns

The canonical frame timestamp used for analysis is:

t_frame = t_after_read_ns

This timestamp represents the moment the frame becomes available to user-space
software.

### 3.2 Implications

- Timestamps include USB transfer, buffering, decoding, and scheduling latency.
- Exposure start time is not directly measured.
- Absolute latency is unknown, but **latency stability** is measurable and
    validated.

For motion tracking, stable relative timing is sufficient provided Δt is used
explicitly.

---

## 4. Validation methodology

### 4.1 Acquisition protocol

For each run:

1. The camera is configured via V4L2.
2. A warm-up phase discards initial frames.
3. Frames are captured for a fixed duration.
4. Host monotonic timestamps are recorded for each frame.
5. No image processing or disk IO is performed during acquisition.

Runs were performed for:

- 1 minute,
- 5 minutes,
- 10 minutes,

under three system conditions:

- idle system,
- CPU stress,
- mixed CPU + IO stress.

### 4.2 Derived quantities

From the timestamps:

- Inter-frame interval: $\Delta t_i = t_i - t_{i-1}$
- Effective nominal period: $T_{inferred} = \text{median}(\Delta t)$
- Effective frame rate: $f_{inferred} = 1 / T_{inferred}$

Frame drops are defined relative to the inferred nominal period:

\[\Delta t_i > 1.5 \, T_{inferred}\]

---

## 5. Results

### 5.1 Nominal (no stress) operation

- Effective frame rate: ≈ 50.0 fps
- Dominant inter-frame interval: ≈ 20 ms
- Timing jitter:
    - std(Δt) ≈ 0.7 ms
    - p99(Δt) ≈ 24 ms
- No sustained frame drops.

The Δt distribution shows a dominant peak at ~20 ms and a small secondary peak
near ~24 ms.

This secondary peak corresponds to **host scheduling quantization** and not to
camera frame loss.

Read-block timing statistics closely match Δt statistics, indicating that
`cap.read()` blocks until the next frame is available.

---

### 5.2 CPU stress

Under CPU load:

- Effective frame rate remains ≈ 50 fps.
- The Δt distribution develops heavier tails.
- Occasional Δt values appear near 24–28 ms and ~40–55 ms.

These effects are consistent with missed scheduler wakeups and confirm that
timing jitter is dominated by host scheduling rather than camera instability.

---

### 5.3 CPU + IO stress

Under heavy mixed load:

- Effective frame rate degrades slightly.
- Δt distribution becomes broad and bursty.
- Large timing excursions (Δt > 100 ms) are observed.
- Frequent inferred drops occur.

In this regime, the host cannot service frame delivery in a timely manner, and
uniform sampling assumptions break down.

---

## 6. Interpretation and limitations

1. The camera operates at a **stable internal cadence of ~50 Hz**.
2. Timing jitter under nominal conditions is low and stationary.
3. Host scheduling is the dominant source of non-ideal timing.
4. Under heavy system load, acquisition timing becomes irregular.

This behavior is expected for USB cameras with host-side timestamping and does
not indicate camera malfunction.

---

## 7. Operational recommendations

- Perform acquisition on an otherwise idle system.
- Avoid heavy CPU or IO activity during data collection.
- Always use per-frame timestamps in downstream analysis.
- Never assume constant sampling intervals.

Optional mitigations (if needed):

- CPU affinity for acquisition process.
- Performance CPU governor.
- Higher scheduling priority.

---

## 8. Conclusion

The camera acquisition subsystem is validated for quantitative motion tracking
at an effective sampling rate of approximately 50 fps under nominal operating
conditions.

Timing behavior, jitter sources, and failure modes are characterized and
documented. The subsystem is suitable for use provided downstream tracking
algorithms explicitly account for variable inter-frame timing.



------

## Appendix A — Stress Testing Procedures and Interpretation

### A.1 Purpose

Stress testing is used to probe the **host-side limits** of the camera acquisition subsystem. The goal is not to optimize performance under stress, but to:

-   identify the dominant sources of timing jitter,
-   characterize failure modes,
-   define safe operational boundaries.

Stress tests are **diagnostic**, not part of routine operation.

------

### A.2 General rules

1.  **Do not change camera configuration**
    -   Same resolution, pixel format, exposure, and FPS request must be used.
2.  **Establish a baseline first**
    -   Always run a no-stress acquisition before applying load.
3.  **One stress dimension at a time**
    -   CPU-only, IO-only, or mixed.
4.  **Always record timestamps**
    -   Host monotonic timestamps are mandatory.
5.  **Interpret drops relative to inferred nominal period**
    -   Drops relative to requested FPS are diagnostic only.

------

### A.3 Baseline (no stress)

**Purpose**
Reference behavior under nominal conditions.

**Command**

```bash
python scripts/validate_timing.py \
  --dev /dev/video2 --index 2 \
  --duration 300 \
  --requested-fps 60 \
  --no-lock \
  --warmup-frames 100 \
  --out runs/timing_baseline
```

**Expected signature**

-   Dominant Δt peak at ~20 ms
-   Small secondary peak near ~24 ms
-   Low jitter (std(Δt) ≲ 1 ms)
-   `drops_inferred_nominal ≈ 0`

------

### A.4 Stress Test A — CPU load (scheduler pressure)

**Purpose**
Evaluate sensitivity to OS scheduling latency.

**Apply load (separate terminal)**

```bash
yes > /dev/null
```

Increase load (one per core):

```bash
for i in {1..4}; do yes > /dev/null & done
```

Stop load:

```bash
pkill yes
```

**Run acquisition**

```bash
python scripts/validate_timing.py \
  --dev /dev/video2 --index 2 \
  --duration 300 \
  --requested-fps 60 \
  --no-lock \
  --warmup-frames 100 \
  --out runs/timing_cpu_stress
```

**Expected signature**

-   Effective FPS unchanged
-   Wider Δt tails
-   Increased p95/p99
-   More weight in secondary peaks (~24–28 ms)
-   Occasional longer Δt (~40–60 ms)
-   Small number of inferred drops

------

### A.5 Stress Test B — IO load

**Purpose**
Evaluate impact of disk and filesystem contention.

**Apply IO load**

```bash
dd if=/dev/zero of=/tmp/io_stress_test bs=1M count=4096 oflag=direct
rm /tmp/io_stress_test
```

**Run acquisition**

```bash
python scripts/validate_timing.py \
  --dev /dev/video2 --index 2 \
  --duration 300 \
  --requested-fps 60 \
  --no-lock \
  --warmup-frames 100 \
  --out runs/timing_io_stress
```

**Expected signature**

-   Increased jitter relative to baseline
-   Read-block histogram mirrors Δt distribution
-   Usually milder than CPU stress

------

### A.6 Stress Test C — Mixed CPU + IO + memory (worst case)

**Purpose**
Identify acquisition failure boundaries.

**Using `stress-ng` (recommended)**

Install once:

```bash
sudo apt install stress-ng
```

Apply stress:

```bash
stress-ng \
  --cpu 4 \
  --io 2 \
  --vm 1 \
  --vm-bytes 1G \
  --timeout 330s
```

Run acquisition during stress:

```bash
python scripts/validate_timing.py \
  --dev /dev/video2 --index 2 \
  --duration 300 \
  --requested-fps 60 \
  --no-lock \
  --warmup-frames 100 \
  --out runs/timing_mixed_stress
```

**Expected signature**

-   Inferred FPS may drift
-   Broad, burst-like Δt distribution
-   Large p99 and max Δt (≫40 ms)
-   Many inferred drops
-   Significant drift vs inferred nominal period

This regime marks **non-operational conditions**.

------

### A.7 Optional experiments

#### CPU frequency scaling

```bash
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
sudo cpupower frequency-set -g performance
```

Repeat baseline acquisition and compare jitter.

#### Scheduling priority

```bash
sudo chrt -f 50 python scripts/validate_timing.py ...
```

or CPU affinity:

```bash
taskset -c 2 python scripts/validate_timing.py ...
```

Expected effect: reduced tail weight and fewer long Δt events.

------

### A.8 Plotting and analysis

After any stress test:

```bash
python scripts/plot_timing_runs.py \
  --runs runs/timing_cpu_stress runs/timing_mixed_stress \
  --requested-fps 60
```

Key plots:

-   `dt_hist.png`
-   `read_block_hist.png`
-   `drift_vs_inferred.png`
-   `drops_timeseries.png`

------

### A.9 Interpretation guide

| Observation                  | Interpretation                  |
| ---------------------------- | ------------------------------- |
| Stable main Δt peak          | Camera cadence stable           |
| Secondary peak at +4 ms      | OS scheduler quantization       |
| Long Δt followed by short Δt | Buffered delivery after stall   |
| Drift vs inferred ≈ 0        | Acquisition timebase coherent   |
| Large drift vs inferred      | Host cannot service acquisition |
| read_block ≈ Δt              | Blocking read dominates timing  |

------

### A.10 Operational conclusion

Stress tests define the **limits of reliable operation**. Normal data acquisition
must be performed well within these limits, on an otherwise idle system, using
explicit per-frame timestamps in downstream analysis.



Below is **Appendix B**, written to **drop in immediately after Appendix A** in your `docs/acquisition_validation.md`. It is formal, self-contained, and bridges acquisition → tracking → physics without implementation noise.

------

## Appendix B — Tracking and Analysis with Explicit Time Handling

### B.1 Motivation

The camera acquisition subsystem produces frames with **non-uniform inter-frame timing** due to host-side scheduling and buffering effects. While the effective frame rate is stable under nominal conditions, small timing variations are unavoidable and have been experimentally characterized.

As a consequence, **downstream tracking and physical analysis must not assume uniform sampling**. Instead, each measurement must be treated as a pair:
\[(x_i, t_i)\]
where:

-   $( x_i )$ represents the tracked quantity (e.g. pixel position, angle),
-   $( t_i )$ is the host-assigned timestamp corresponding to that frame.

This appendix formalizes how tracking and analysis must be performed using the explicit timestamps.

------

### B.2 Data model

For each frame $i$, the tracking stage must output at minimum:

-   frame index  $i$
-   timestamp $t_i$ (monotonic, in seconds),
-   tracked observable $x_i$ (or $\theta_i$ ) for angular motion).

The resulting dataset is an **irregularly sampled time series**:
${(t_i, x_i)}_{i=0}^{N-1}$

The inter-frame interval is defined as:
$\Delta t_i = t_i - t_{i-1}$

No assumption is made that $\Delta t_i $ is constant.

------

### B.3 First derivatives (velocity)

For irregular sampling, velocity must be computed using the actual time differences.

A first-order estimate is:
$v_i = \frac{x_i - x_{i-1}}{t_i - t_{i-1}}$

This formulation:

-   is unbiased by timing jitter,
-   reduces to the standard finite difference when sampling is uniform,
-   remains valid under moderate scheduling-induced timing variations.

------

### B.4 Second derivatives (acceleration)

Second derivatives require special care for non-uniform grids.

## A symmetric, second-order accurate estimate is:

$a_i = 2 \, \frac{ \frac{x_{i+1}-x_i}{t_{i+1}-t_i} - \frac{x_i-x_{i-1}}{t_i-t_{i-1}}}{t_{i+1}-t_{i-1}}$

This expression:

-   reduces numerical bias caused by variable $\Delta t$,
-   avoids assuming a fixed sampling interval,
-   is suitable for angular acceleration estimation in pendulum dynamics.

------

### B.5 Frequency and period estimation

Uniform-sampling methods (e.g. FFT with fixed Δt) implicitly assume constant spacing and can produce biased frequency estimates when applied directly.

Recommended approaches with explicit timestamps:

#### Peak or zero-crossing analysis

-   Identify extrema or zero crossings in $x_i$,
-   Use the corresponding timestamps $t_i$,
-   Compute periods directly: $T_k = t_{k+1} - t_k$

#### Model-based fitting

Fit a continuous-time model directly to the data: $x(t) = A \cos(\omega t + \phi) + c$
using nonlinear least squares with the measured $t_i$.

This approach:

-   naturally handles irregular sampling,
-   averages over timing jitter,
-   yields robust frequency estimates.

------

### B.6 Interpolation and resampling (optional)

Resampling to a uniform grid is **not required** and should only be done if justified.

If resampling is necessary:

-   interpolate $x(t)$ using the measured timestamps,
-   document the interpolation method explicitly,
-   never discard the original $(t_i, x_i)$ data.

Blind resampling without timestamp awareness is discouraged.

------

### B.7 Real-time tracking implications

In real-time operation:

-   each frame must be timestamped at acquisition,
-   the timestamp must be passed to the tracking stage,
-   any rate-based quantity (velocity, acceleration) must be computed using $t_i$.

A recommended processing chain is:

1.  **Acquisition** → frame + timestamp
2.  **Tracking** → $(x_i, t_i)$
3.  **Physics layer** → explicit-time analysis

This ensures robustness against OS scheduling effects and backend changes.

------

### B.8 Relation to acquisition validation

The acquisition validation demonstrated:

-   low jitter under nominal load,
-   bounded and explainable timing deviations,
-   clear failure modes under heavy system stress.

Explicit time handling ensures that:

-   nominal jitter does not bias results,
-   stress-induced irregularity is detectable and quantifiable,
-   tracking correctness is preserved whenever acquisition remains within validated limits.

------

### B.9 Practical rule

>   **Tracking algorithms must treat timestamps as primary data, not metadata.**

This principle guarantees that the measurement pipeline remains physically correct and reproducible, even when real-world timing imperfections are present.

