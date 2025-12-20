# Camera-Based 2D Pendulum Measurement System

## Overview
This project implements a camera-based instrument for measuring the planar motion
of a physical pendulum, with emphasis on:
- Instrument definition
- Calibration and validation
- Timing and spatial accuracy
- End-to-end measurement pipeline

## Repository Structure



```bash
├── docs/              # LaTeX, notes, presentations
├── src/               # Core source code
├── calib/             # Calibration routines
├── analysis/          # Data analysis scripts
├── cad/               # Build123d source models
├── config/            # YAML/JSON configuration
└── README.md


```



------

## 1. Directory skeleton

```text
pendulum-camera-lab/
  README.md
  LICENSE

  docs/
    overview.md
    theory_pendulum.md
    camera_and_calibration.md
    tracking_and_uncertainty.md
    validation_and_results.md

  hardware/
    camera_specs_ELP.md
    pendulum_setup.md
    lighting_and_background.md

  acquisition/
    README.md          # What this part will do, config philosophy
    capture_config_example.yaml
    NOTES_acquisition.md

  processing/
    README.md          # Tracking approach, design decisions
    NOTES_tracking.md

  calibration/
    README.md
    calibration_plan.md
    calibration_images/   # Placeholder, gitignored if you want
      .gitkeep

  analysis/
    README.md
    NOTES_period_fit.md
    NOTES_error_budget.md

  experiments/
    README.md
    exp_01_baseline/
      README.md
      raw/              # Raw videos / images (probably gitignored)
      processed/        # CSV, JSON, plots, etc.
    exp_02_length_scan/
      README.md
      raw/
      processed/

  presentation/
    winter_school_pendulum.tex
    figures/
      pipeline_schematic.pdf
      setup_photo.png
      sample_track_overlay.png

  .gitignore
```

You don’t *have* to create all files now; it’s enough to create empty placeholders where you want to start writing.

------

## 2. `README.md` draft

# Camera-Based Pendulum Lab Instrument

A small but serious project to treat a **camera + pendulum** as a proper
measurement instrument. The goal is to build a **reproducible, documented
pipeline** from video acquisition to physical measurements, including:

- Controlled camera operation (ELP USB camera).
- Real-time / offline tracking of a 2D pendulum.
- Calibration from pixels to physical coordinates.
- Characterization of accuracy, noise, and systematics.
- Validation against the physics of a pendulum.
- Teaching material (winter school lecture) and open documentation.

This repo is intended both as:

- a **template** for camera-based measurement systems in teaching labs, and  
- a **case study** in treating simple setups with “instrument-level” rigor.

---

## 1. Motivation

Low-cost USB cameras are everywhere, but they’re often treated as gadgets,
not as instruments. In this project we take a familiar system – a pendulum –
and ask:

> How far can we go in turning a cheap camera into a **quantitative sensor**
> with known uncertainty and limitations?

Along the way, we cover practical topics:

- camera control and reproducibility;
- image processing and robust tracking;
- geometric calibration;
- uncertainty estimation and validation against theory.

This makes it suitable for **students** (winter school / lab course) and
for **instructors** designing modern experimental activities.

---

## 2. High-level pipeline

The measurement chain can be summarized as:

```text
Physical pendulum
      ↓
Optical image formation (camera, lens, lighting)
      ↓
Digital video frames (controlled acquisition)
      ↓
Image processing & tracking (pendulum position in pixels)
      ↓
Calibration (pixels → meters, time base → seconds)
      ↓
Physical observables (angle, amplitude, period, energy, etc.)
      ↓
Analysis & validation (model fits, error budget)
```

This repo is organized to mirror that flow.

------

## 3. Repository structure

```text
docs/                 # Conceptual and technical documentation
hardware/             # Experimental setup, camera + pendulum details
acquisition/          # Camera control and video acquisition tools
processing/           # Image processing and pendulum tracking
calibration/          # Pixel → physical mapping, camera geometry
analysis/             # Period fits, models, validation plots
experiments/          # Concrete experiment runs (data + notes)
presentation/         # Beamer slides for the winter school talk
```

### 3.1 `docs/`

Narrative documentation:

-   `overview.md`
     Big-picture description of the system and the goals.
-   `theory_pendulum.md`
     Pendulum physics used in the project: small-angle approximation,
     large-angle corrections (as needed), and what we actually measure.
-   `camera_and_calibration.md`
     Camera model assumptions, calibration methods, and practical procedures.
-   `tracking_and_uncertainty.md`
     How tracking works, typical failure modes, and uncertainty estimates.
-   `validation_and_results.md`
     Key plots: period vs length, noise measurements, example datasets.

### 3.2 `hardware/`

Details of the experimental setup:

-   `camera_specs_ELP.md`
     ELP camera model, lens, fixed configuration (resolution, fps, etc.).
-   `pendulum_setup.md`
     Geometry, dimensions, mounting, choice of bob, string/rod, etc.
-   `lighting_and_background.md`
     Background color/texture, light sources, any shielding against reflections.

These documents should make it possible for someone else to **rebuild** the
 setup with similar performance.

### 3.3 `acquisition/`

Tools for **controlling the camera** and recording data.

Planned contents:

-   Config file (e.g. `capture_config_example.yaml`) to fix:
    -   camera device ID,
    -   resolution, fps,
    -   exposure, gain, white balance,
    -   output file formats and paths.
-   Scripts (later) for:
    -   live preview for focusing and framing,
    -   recording calibration videos,
    -   recording experiment runs with associated metadata.
-   `NOTES_acquisition.md` for any OS-specific quirks
     (e.g. Linux `v4l2-ctl` commands, USB bandwidth issues).

### 3.4 `processing/`

Image processing and tracking logic (separated from acquisition):

-   Tracking strategy (e.g. colored marker on bob, thresholding).
-   Frame-by-frame detection and pose estimation.
-   Output format for tracked time series:
    -   time stamps,
    -   pixel coordinates,
    -   quality/confidence metrics.

This separation allows the same tracking code to be used in:

-   online mode (live camera stream), and
-   offline mode (existing video files).

### 3.5 `calibration/`

Everything related to **mapping pixels to physical coordinates** and
 correcting camera distortions.

-   `calibration_plan.md` describes:
    -   chosen calibration method (simple scale vs full camera model),
    -   calibration targets (ruler, checkerboard, etc.),
    -   procedures and recommended frequency.
-   `calibration_images/` holds example calibration frames or image sets
     (reduced or compressed if stored in the repo).

The goal is to obtain:

-   a mapping from `(u, v)` pixel coordinates to `(x, y)` in meters; and
-   estimates of the associated uncertainties.

### 3.6 `analysis/`

Data analysis and validation:

-   Extracting the pendulum angle as a function of time.
-   Estimating period, damping, and other parameters.
-   Comparing with theoretical models:
    -   small-angle approximation,
    -   possible large-angle corrections as a “bonus”.

`NOTES_period_fit.md` and `NOTES_error_budget.md` can hold the reasoning and
 equations behind the scripts / notebooks.

### 3.7 `experiments/`

Concrete experiment runs, each in its own subdirectory:

Example:

```text
experiments/
  exp_01_baseline/
    README.md      # Conditions: length, amplitude, settings, date, etc.
    raw/           # Raw videos (or paths / symlinks if stored elsewhere)
    processed/     # Tracking output, analysis results
```

Here we document:

-   how each experiment was performed,
-   what settings were used,
-   and what conclusions were drawn.

This is where the “instrument character” becomes visible.

### 3.8 `presentation/`

Materials for a ~40-minute winter school talk:

-   `winter_school_pendulum.tex` – Beamer source.
-   `figures/` – pipeline schematics, setup photos, example plots.

The talk is meant to be **self-contained**: a student can watch it, then
 explore this repo to see all the details.

------

## 4. Status and roadmap

**Current status:**
 Structure and documentation are being set up. Code is intentionally minimal
 or absent at this stage to keep the design clear.

**Next steps:**

1.  Finalize and document the experimental setup in `hardware/`.
2.  Decide and document the minimum viable calibration strategy in `docs/` and `calibration/`.
3.  Implement a first acquisition script with fixed camera settings.
4.  Add a simple, robust tracking pipeline for the pendulum bob.
5.  Record first baseline experiment and perform preliminary analysis.
6.  Iterate on calibration and error estimates.
7.  Polish documentation and winter school presentation.

------

## 5. License and citation

-   License: (to be decided – for example MIT or BSD-3-Clause).
-   If you use this project in teaching or a lab course, please consider
     citing the repository and acknowledging the original authors.

------

```
If you want, next step we can:

- fill in one or two of the `docs/*.md` files (e.g. `overview.md` + `camera_and_calibration.md`) with more detailed text, still without any code.
```
