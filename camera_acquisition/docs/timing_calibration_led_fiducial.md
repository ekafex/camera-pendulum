# Optical Timing Calibration Using an LED Fiducial

## 1. Purpose

This document describes a planned optical timing calibration experiment for the
camera acquisition subsystem. The goal is to relate host-assigned frame timestamps
to an external, known time reference observable in the image data.

Unlike timing characterization (which studies internal consistency of timestamps),
this procedure enables partial or full calibration of the acquisition time model
relative to a known temporal standard.

---

## 2. Motivation

The current acquisition system assigns timestamps in host user-space when frames
become available. While these timestamps are stable and well-characterized,
they are not calibrated to the true physical exposure time.

An external optical time fiducial provides:
- validation of timestamp rate accuracy (clock scaling),
- measurement of relative timing jitter with respect to a known reference,
- potential estimation of latency and drift.

---

## 3. Principle of the method

An LED placed in the camera’s field of view is driven by a known electrical signal
(e.g., square wave from a function generator).

Let:
- \( T_0 \) be the known period of the LED modulation,
- \( t_k^{\mathrm{ref}} \) be the true transition times of the LED,
- \( \hat{t}_k \) be the host timestamps of detected transitions in the video.

By comparing \( \hat{t}_k \) to the expected timing structure of the reference,
the following can be measured:

- **rate accuracy**: does the camera/host timebase match the reference period?
- **drift**: does the phase error accumulate over time?
- **jitter**: what is the statistical spread of detected transition times?
- **failure modes**: missed transitions, burst behavior, stress sensitivity.

Absolute epoch alignment is not required for most applications; relative timing
and rate accuracy are sufficient.

---

## 4. Hardware setup

### 4.1 LED selection

Commodity LEDs are acceptable for low-frequency (50–200 Hz) calibration provided:

- the LED is driven well below its maximum current,
- the driver circuit provides fast rise/fall times relative to exposure time.

Important note:
The intrinsic optical response time of most LEDs is extremely fast (ns–µs).
In practice, **driver electronics**, not the LED die, dominate switching speed.

### 4.2 LED driver

Recommended options:
- Function generator (square wave) → resistor → LED
- Function generator → transistor/MOSFET → LED (preferred for sharper edges)

Typical settings:
- Frequency: 50 Hz or 100 Hz
- Duty cycle: 30–70%
- Amplitude: sufficient to ensure high contrast in camera image

If available, verify the optical waveform using a photodiode + oscilloscope.

---

## 5. Camera configuration constraints

For meaningful calibration:

- Exposure time must be short enough that LED transitions are not excessively smeared.
- Gain should be fixed.
- Auto-exposure and auto-gain must be disabled.
- The LED should occupy a small, fixed ROI in the image.

If rolling shutter is present:
- use a compact LED image,
- keep vertical position fixed across runs,
- document ROI geometry.

---

## 6. Data acquisition procedure

1. Configure the camera using the validated acquisition setup.
2. Start LED modulation at known frequency \( T_0 \).
3. Acquire frames and host timestamps \( \hat{t}_i \).
4. Store:
   - frame index,
   - host timestamp,
   - full frame or LED ROI intensity.

No additional synchronization is required.

---

## 7. Data analysis

### 7.1 ROI intensity extraction

For each frame:
- extract mean or median intensity in a fixed LED ROI,
- produce a time series \( I_i = I(\hat{t}_i) \).

### 7.2 Transition detection

Detect LED on/off transitions using:
- threshold crossing,
- derivative peak,
- or template matching.

Each detected transition yields an event time \( \hat{t}_k \).

---

## 8. Calibration quantities

From the detected transitions:

### 8.1 Period accuracy
\[
\Delta \hat{t}_k = \hat{t}_{k+1} - \hat{t}_k
\]

Compare:
\[
\alpha = \frac{\mathrm{median}(\Delta \hat{t}_k)}{T_0}
\]

This measures clock-rate accuracy and effective drift.

### 8.2 Jitter
\[
\sigma_{\mathrm{jitter}} = \mathrm{std}(\Delta \hat{t}_k - T_0)
\]

### 8.3 Phase drift
Fit cumulative phase error:
\[
\phi_k = \hat{t}_k - k T_0
\]

A linear trend indicates drift; random scatter indicates jitter.

---

## 9. Interpretation and limitations

- This method calibrates **timing rate and stability**, not absolute exposure epoch.
- Exposure integration blurs transitions; the detected event corresponds to an
  intensity-weighted time within the exposure window.
- Rolling shutter introduces spatial dependence of apparent transition time.
- Host scheduling effects remain visible in jitter tails.

These limitations must be documented explicitly with the results.

---

## 10. Relation to acquisition model

This experiment empirically constrains the forward timing model:

\[
\hat{t}_i = t_i^{\mathrm{exp}} + \delta + \eta_i
\]

by providing information about:
- the scaling between \( \hat{t} \) and a physical reference,
- the statistical properties of \( \eta_i \),
- and the stability of the acquisition timebase.

---

## 11. Deliverables

A completed calibration should include:
- description of LED drive and verification,
- plots of ROI intensity vs time,
- transition timing residuals,
- estimated rate error, drift, and jitter,
- explicit statement of limitations.

---

## 12. Status

This procedure is planned but not yet executed.
Timing characterization without external reference remains valid and sufficient
for current pendulum tracking objectives.

