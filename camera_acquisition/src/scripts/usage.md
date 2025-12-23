# Usage of the scripts

### Usage of the `scripts/camera_lock_v4l2.py`

Identify the device node:

```bash
v4l2-ctl --list-devices
```

Run the lock script (example):

```bash
python3 scripts/camera_lock_v4l2.py --dev /dev/video2 --enforce-50hz
```

You should see a report with [ OK ] lines and a runs/camera_lock_YYYYMMDD_HHMMSS/ folder containing the V4L2 snapshots.



### Usage of the  `scripts/validate_timing.py`

check by running:

```bash
python scripts/validate_timing.py --dev /dev/video2 --index 2 --width 1280 --height 720 --requested-fps 60 --no-lock --warmup-frames 100 --duration 60 --out scripts/runs/timing_720p_req60_60s_v1
```

Then do **5 minutes** test:

```bash
python scripts/validate_timing.py --dev /dev/video2 --index 2 --width 1280 --height 720 --requested-fps 60 --no-lock --warmup-frames 100 --duration 300 --out scripts/runs/timing_720p_req60_300s_v1

```

Then do **10 minutes stress** (while running a CPU load in another terminal):

```bash
python scripts/validate_timing.py --dev /dev/video2 --index 2 --width 1280 --height 720 --requested-fps 60 --no-lock --warmup-frames 100 --duration 600 --out scripts/runs/timing_720p_req60_600s_v1
```



### Usage of the  scripts/plot_timing_runs.py

Generate plots (both “vs inferred” and “vs requested”)

```bash
python scripts/plot_timing_runs.py --runs scripts/runs/timing_720p_req60_60s_v1 --requested-fps 60
```

