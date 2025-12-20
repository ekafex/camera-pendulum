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
python3 scripts/validate_timing.py \
  --dev /dev/video2 \
  --index 2 \
  --duration 60 \
  --out runs/timing_720p60_60s_01

```

Then do **5 minutes** test:

```bash
python3 scripts/validate_timing.py --dev /dev/video2 --index 2 --duration 300 --out runs/timing_720p60_5min_01
```

Then do **10 minutes stress** (while running a CPU load in another terminal):

```bash
python3 scripts/validate_timing.py --dev /dev/video2 --index 2 --duration 600 --out runs/timing_720p60_10min_stress_01
```

