# Camera Acquisition Time Model: Characterization, Limitations, and Calibration Path

## 1. Scope and objective

This note formalizes the timing model used in the camera acquisition subsystem for the pendulum tracking pipeline. It clarifies:

- what timestamps mean in the current implementation,
- what was *characterized* (validated empirically) versus what was not *calibrated* (referenced to an external time standard),
- what assumptions are embedded in the forward timing model,
- what inverse timing quantities can and cannot be inferred from the data,
- and how a full timing calibration can be performed in a later stage.

This document is intentionally rigorous because time handling affects downstream tracking (derivatives, frequency estimation, parameter fitting) and reproducibility.

---

## 2. Definitions and notation

We distinguish three time domains:

1) **Physical time** (ground truth, not directly observed)
- \( t \): the true physical time at which photons hit the sensor.
- \( t_i^{\mathrm{exp}} \): a representative exposure time for frame \(i\), e.g. start-of-exposure, mid-exposure, or end-of-exposure.

2) **Camera / firmware time** (rarely exposed for cheap UVC devices)
- \( t_i^{\mathrm{cam}} \): camera-internal clock time for exposure or frame generation.
- Not assumed available unless the camera provides reliable metadata timestamps.

3) **Host time** (what we currently record)
- \( \hat{t}_i \): host monotonic timestamp assigned in software when a frame becomes available to user-space.
- In code, this is `t_after_read_ns * 1e-9` (seconds).

We also define:
- inter-frame interval: \( \Delta \hat{t}_i = \hat{t}_i - \hat{t}_{i-1} \)
- inferred nominal period: \( \hat{T} = \mathrm{median}(\Delta \hat{t}_i) \)
- inferred effective frame rate: \( \hat{f} = 1/\hat{T} \)

---

## 3. Current timestamp definition (what we measure)

In the current acquisition implementation, each successful frame produces two host timestamps:

- `t_before_read_ns`: host monotonic timestamp immediately before `cap.read()`
- `t_after_read_ns`: host monotonic timestamp immediately after `cap.read()` returns successfully

We define the canonical frame timestamp as:
\[
\boxed{
\hat{t}_i = t^{\mathrm{after}}_i
}
\]

Interpretation:
- \( \hat{t}_i \) is the time the frame becomes available to the acquisition process in user-space.
- It is not (in general) equal to start-of-exposure time, mid-exposure time, or end-of-exposure time.

We also measure:
\[
\tau_i^{\mathrm{read}} = t^{\mathrm{after}}_i - t^{\mathrm{before}}_i
\]
which is the *blocking duration* of `cap.read()`. In practice this often matches the frame cadence and reveals scheduling-induced latency.

---

## 4. Forward timing model (instrument model)

### 4.1 Conceptual pipeline

A realistic acquisition pipeline is:

\[
\text{Scene}(t)
\;\xrightarrow{\text{optics + sensor + exposure}}\;
\text{raw frame}
\;\xrightarrow{\text{camera processing + MJPG encode}}\;
\text{USB transfer}
\;\xrightarrow{\text{kernel / V4L2 buffering}}\;
\text{OpenCV decode + user-space}
\;\rightarrow\;
\hat{t}_i
\]

The forward timing mapping is therefore:

\[
\boxed{
\hat{t}_i = g(t_i^{\mathrm{exp}}) = t_i^{\mathrm{exp}} + \delta + \eta_i
}
\]

Where:
- \( \delta \) is an *unknown constant (or slowly varying)* offset capturing average latency from exposure to user-space availability.
- \( \eta_i \) is a stochastic term capturing:
  - OS scheduling jitter,
  - buffering variability,
  - decode latency variability,
  - occasional stalls.

This is the minimal forward model required to reason about timestamps.

### 4.2 Effective sampling model

Even if camera exposure is periodic, host timestamps show non-uniform sampling:

\[
\boxed{
\hat{t}_i = \hat{t}_0 + i\hat{T} + \varepsilon_i
}
\]

Where:
- \( \hat{T} \) is the effective sampling period in host time (empirically measurable),
- \( \varepsilon_i \) is zero-mean (approximately) stationary jitter under nominal operating conditions,
- \( \varepsilon_i \) becomes heavy-tailed and non-stationary under system stress.

This is the model we validated empirically.

---

## 5. What we performed: timing characterization (not full calibration)

### 5.1 Characterization vs calibration

**Characterization** answers:
- What is the observed effective frame cadence in host time?
- How stable is it over minutes?
- What is the distribution of \( \Delta \hat{t} \)?
- How do tails and stalls behave under CPU and IO stress?
- Under what conditions does the acquisition contract break?

**Calibration** answers (requires an external reference):
- What is the relationship between \( \hat{t}_i \) and the true exposure time \( t_i^{\mathrm{exp}} \)?
- What is the absolute latency \( \delta \)?
- Does the host timestamp run at the same rate as the physical time standard (clock-rate error/drift)?
- What is the absolute jitter relative to the reference standard?

In our current work, we performed **timing characterization**:
- we quantified \( \hat{T} \), \( \hat{f} \), and the jitter/stall statistics in host time,
- we identified host scheduling as the dominant source of tails,
- we defined operational conditions for reliable acquisition.

We did **not** perform a full calibration because we did not introduce a known external timing fiducial (i.e., no access to \( t_i^{\mathrm{exp}} \) or a synchronized observable event in the scene).

---

## 6. Limitations of the current time model

### 6.1 No absolute mapping to exposure time

Without a time reference in the optical signal (or camera-provided exposure timestamps), we cannot estimate:
- the absolute latency \( \delta \),
- whether the timestamp corresponds better to start-of-exposure, mid-exposure, or end-of-exposure.

Therefore, \( \hat{t}_i \) must be interpreted strictly as *frame availability in user-space*.

### 6.2 Unknown exposure-time semantics

Even if we knew \( \delta \), exposure is not instantaneous. For exposure duration \( t_{\mathrm{exp}} \):
- the scene is integrated over an interval,
- a time fiducial in the scene will appear smeared if it changes within an exposure.

A practical time reference may therefore calibrate the timing of *observed intensity transitions* rather than exposure start time directly.

### 6.3 Rolling shutter effects (if present)

Many USB cameras use rolling shutter. This means:
- different rows correspond to slightly different exposure times,
- an LED transition can appear skewed depending on its vertical position in the image.

If rolling shutter is present, a full timing calibration must specify which row/region defines the event time, or use a small ROI and a consistent geometry.

### 6.4 Host scheduling and buffering

Our characterization showed discrete timing modes (e.g., ~20 ms main peak plus secondary peak near ~24 ms).
This is consistent with host scheduling quantization (e.g., scheduler tick effects) and buffering behavior.

Under mixed CPU+IO stress, the distribution becomes bursty:
- long intervals followed by short intervals,
- many inferred stalls/drops relative to nominal cadence.

This does not imply camera malfunction; it defines the failure boundary of the host acquisition process.

### 6.5 Implication for downstream tracking

Because \( \Delta \hat{t}_i \) is not perfectly constant, downstream processing must treat data as:
\[
(x_i, \hat{t}_i)
\]
and compute any time derivatives or frequency fits using explicit timestamps.

---

## 7. Inverse time model (what can be inferred)

### 7.1 Inverse problem statement

A “time calibration” inverse problem would attempt to infer:
\[
t_i^{\mathrm{exp}} = g^{-1}(\hat{t}_i)
\]

But in general \(g\) is not invertible from host timestamps alone, because:
- \( \delta \) is unknown,
- \( \eta_i \) is random,
- and there is no independent observation of \( t_i^{\mathrm{exp}} \).

Therefore, with only \( \hat{t}_i \), the best we can infer is the **effective sampling behavior**:
- \( \hat{T} \) (effective period),
- jitter distribution,
- stall frequency.

This is sufficient for robust tracking if timestamps are used explicitly, but it is not a physical-time calibration.

---

## 8. How to achieve full timing calibration (planned future work)

A full calibration requires an external reference observable in the frames, with known timing properties.

### 8.1 Optical time fiducial using LED + function generator (recommended)

**Idea**
- Place an LED in the field of view.
- Drive it with a function generator at a known frequency (e.g., 50 Hz, 100 Hz) with a sharp duty cycle.
- Record frames and extract LED ROI intensity \( I_i \).

**What this calibrates**
- The **timebase rate** of \( \hat{t} \) relative to the reference (period accuracy, drift).
- The **jitter** of event detection in \( \hat{t} \).
- Potentially the **latency offset** \( \delta \) up to a constant phase ambiguity, depending on waveform choice.

**Procedure**
1. Configure LED drive:
   - Square wave, TTL-level if possible (via driver transistor if required).
   - Prefer duty cycle not too small (avoid missed pulses under exposure integration).
2. Acquire video frames and timestamps \(\hat{t}_i\).
3. For each frame, compute ROI intensity \( I_i \).
4. Detect transitions (edges) or peaks to obtain event times \(\hat{t}_{k}\).
5. Compare event intervals to the known reference period \(T_0\):
   \[
   \Delta \hat{t}_k = \hat{t}_{k+1} - \hat{t}_k
   \]
   and estimate:
   - rate error: \( \alpha = \mathrm{median}(\Delta \hat{t}_k)/T_0 \)
   - drift: linear trend in cumulative phase error
   - jitter: residual dispersion after removing drift

**Caveats**
- Exposure time must be small enough that transitions are not excessively smeared.
- If rolling shutter exists, use a compact ROI and stable geometry.
- The LED driver, not the LED die, often dominates edge speed.

### 8.2 LED switching speed: practical guidance (without relying on vendor datasheets)

Commodity indicator LEDs typically have intrinsic optical response times that are very fast (often in the ns–µs regime),
but the *effective* on/off transition time in an experiment is dominated by:
- driver rise/fall time (output impedance, transistor saturation),
- wiring capacitance,
- current limiting configuration,
- function generator output characteristics,
- and camera exposure integration.

Therefore, instead of depending on retail datasheets, a robust approach is:
- validate the LED drive waveform using a **photodiode + oscilloscope** (or a fast phototransistor),
- confirm the optical transition time and duty cycle under the actual circuit.

For 50–200 Hz reference signals, even relatively slow LED drivers are typically adequate, but measurement rigor requires verification.

### 8.3 Kernel / V4L2 buffer timestamps (alternative path)

Instead of host timestamps around `cap.read()`, one can use V4L2 buffer timestamps assigned in the kernel capture path.
This can reduce user-space scheduling influence and can be closer to the actual capture timing (depending on driver/camera).

This requires a V4L2 capture interface (not plain OpenCV abstraction), and careful interpretation of:
- timestamp origin (monotonic vs realtime),
- whether timestamps represent start-of-frame, end-of-frame, or dequeue time.

Even with kernel timestamps, an optical fiducial remains valuable for absolute validation.

### 8.4 Hardware trigger / synchronization (advanced)

A higher-end timing calibration uses hardware:
- camera trigger input (global shutter industrial cameras),
- shared clock or PTP synchronized timebase,
- external strobe controlled by the same reference clock.

This is typically outside the scope of low-cost UVC cameras but is listed for completeness.

---

## 9. Assumptions summary

### Forward timing model assumptions (current)
- Host monotonic timestamps are stable and suitable for relative timing.
- Under nominal load, \( \varepsilon_i \) is stationary with bounded tails.
- The effective cadence \( \hat{T} \) is meaningful and reproducible.
- Timestamp corresponds to user-space availability, not exposure.

### Inverse timing model assumptions (for full calibration)
- The external fiducial has timing accuracy significantly better than the observed jitter.
- Fiducial transitions are detectable in frames (sufficient SNR).
- Camera exposure integration does not erase transition timing beyond acceptable uncertainty.
- Geometry/rolling shutter effects are controlled or modeled.

---

## 10. Practical outcome for the pendulum pipeline

Even without full calibration to exposure time, the characterized time model is sufficient for accurate pendulum tracking provided:
- each frame carries its timestamp,
- all derivatives and fits use explicit \( \hat{t}_i \),
- acquisition runs under nominal load.

A later full calibration using an LED optical fiducial can:
- validate clock-rate accuracy against a reference,
- quantify absolute time mapping uncertainty,
- support multi-sensor synchronization if required.

---

## 11. Recommended future deliverables (optional)

When the LED reference experiment is implemented, add:

- `docs/timing_calibration_led_fiducial.md` (procedure, circuits, and results)
- a script that:
  - extracts ROI intensity vs time,
  - detects edges,
  - estimates rate error, drift, and jitter,
  - produces plots suitable for documentation.

