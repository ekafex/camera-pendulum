Below is a **practical, drop-in cheat sheet** you can keep in the repo (e.g. `docs/stress_testing_cheat_sheet.md`). It is written as an **operator’s guide**, not a tutorial, and matches exactly what you have been doing in this project.

------

# Stress Testing Cheat Sheet

**Camera Acquisition & Timing Validation**

## Purpose

Stress tests are used to **probe the limits of host-side scheduling and I/O** and to verify how camera acquisition timing degrades under load. They help distinguish:

-   camera-limited behavior
-   USB / driver behavior
-   OS scheduling and resource contention

They are **not** meant to be run routinely—only when validating or re-validating the acquisition subsystem.

------

## General Rules (Read First)

1.  **Never change camera settings during stress tests**
    -   Same resolution, format, exposure, FPS request
2.  **One stress dimension at a time**
    -   CPU-only, IO-only, mixed
3.  **Always record timestamps**
    -   Host monotonic timestamps are mandatory
4.  **Interpret drops relative to inferred nominal FPS**
    -   Drops vs requested FPS are diagnostic only
5.  **Baseline first**
    -   Always run a no-stress test before stressing

------

## Baseline (No Stress)

### Purpose

Reference behavior under nominal conditions.

### Command

```bash
python scripts/validate_timing.py \
  --dev /dev/video2 --index 2 \
  --duration 300 \
  --requested-fps 60 \
  --no-lock \
  --warmup-frames 100 \
  --out runs/timing_baseline
```

### Expected Signature

-   Single dominant Δt peak (~20 ms)
-   Small secondary peak (~24 ms)
-   Low std(Δt)
-   drops_inferred_nominal ≈ 0

------

## Stress Test A — CPU Load (Scheduler Pressure)

### Purpose

Test OS scheduling jitter without disk interference.

### How to Apply Load

In a **separate terminal**:

```bash
yes > /dev/null
```

To increase load (one per core):

```bash
for i in {1..4}; do yes > /dev/null & done
```

Stop load after test:

```bash
pkill yes
```

### Run Acquisition

```bash
python scripts/validate_timing.py \
  --dev /dev/video2 --index 2 \
  --duration 300 \
  --requested-fps 60 \
  --no-lock \
  --warmup-frames 100 \
  --out runs/timing_cpu_stress
```

### Expected Signature

-   Mean FPS unchanged
-   Wider Δt tails
-   Increased p95/p99
-   Secondary peak (~24 ms) more populated
-   Occasional longer Δt (~40–60 ms)
-   Small number of inferred drops

------

## Stress Test B — IO Load (Disk / FS Pressure)

### Purpose

Test impact of heavy disk activity.

### Simple IO Load (safe)

```bash
dd if=/dev/zero of=/tmp/io_stress_test bs=1M count=4096 oflag=direct
rm /tmp/io_stress_test
```

### Run Acquisition (while IO runs)

```bash
python scripts/validate_timing.py \
  --dev /dev/video2 --index 2 \
  --duration 300 \
  --requested-fps 60 \
  --no-lock \
  --warmup-frames 100 \
  --out runs/timing_io_stress
```

### Expected Signature

-   Similar to CPU stress but often milder
-   Increased jitter if filesystem is slow
-   Read-block histogram mirrors Δt

------

## Stress Test C — Mixed CPU + IO + Memory (Worst Case)

### Purpose

Determine failure mode under realistic heavy system usage.

### Using `stress-ng` (recommended)

Install (once):

```bash
sudo apt install stress-ng
```

Run stress:

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

### Expected Signature

-   Inferred FPS may drift
-   Broad Δt distribution
-   Burst-like behavior
-   Large p99 and max Δt (≫40 ms)
-   Many inferred drops
-   Significant drift vs inferred nominal

This marks the **operational failure boundary**.

------

## Optional: CPU Frequency / Power Management Stress

### Purpose

Test wakeup latency effects due to power saving.

### Check governor

```bash
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
```

### Set performance mode (temporary)

```bash
sudo cpupower frequency-set -g performance
```

Repeat baseline test and compare with powersave mode.

------

## Optional: Scheduling Priority Experiment

### Purpose

Test mitigation strategies.

### Run acquisition with higher priority

```bash
sudo chrt -f 50 python scripts/validate_timing.py ...
```

Or pin to a CPU:

```bash
taskset -c 2 python scripts/validate_timing.py ...
```

### Expected Effect

-   Reduced tail weight
-   Smaller p99
-   Fewer long Δt events

------

## Plotting After Any Test

Always generate plots for interpretation:

```bash
python scripts/plot_timing_runs.py \
  --runs runs/timing_cpu_stress runs/timing_mixed_stress \
  --requested-fps 60
```

Key plots to inspect:

-   `dt_hist.png`
-   `read_block_hist.png`
-   `drift_vs_inferred.png`
-   `drops_timeseries.png`

------

## Interpretation Guide (Quick)

| Observation                  | Interpretation                 |
| ---------------------------- | ------------------------------ |
| Stable main peak, small tail | Healthy acquisition            |
| Secondary peak at +4 ms      | OS scheduler tick              |
| Long Δt followed by short Δt | Buffered delivery after stall  |
| Drift vs inferred ≈ 0        | Camera cadence stable          |
| Drift vs inferred large      | Host cannot keep up            |
| read_block ≈ Δt              | Blocking read dominates timing |

------

## When to Re-run Stress Tests

Run stress tests:

-   after kernel or driver updates
-   after moving to a new machine
-   after changing capture backend
-   before final experimental campaigns

Do **not** run them routinely during development.

------

## One-Sentence Rule

>   **Stress tests define the limits; normal operation must stay well inside them.**

If you want, next I can:

-   condense this into a 1-page laminated “lab card”, or
-   integrate it directly into your acquisition documentation as an appendix.
