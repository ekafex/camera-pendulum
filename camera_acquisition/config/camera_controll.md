# Linux USB camera (V4L2-ctl)

On Linux, “camera parameters given by firmware” and “parameters you can control” are both exposed through **V4L2** (for UVC USB cameras). 

The practical way to “remind yourself” is: use `v4l2-ctl` to query 

1.   device identity/capabilities, 

2.   supported formats/modes, and

3.    exposed controls (read-only vs settable). 

Below is the minimal, reliable checklist.

## 1) Identify the camera and its device node

```bash
v4l2-ctl --list-devices
```

This maps the physical camera to `/dev/videoX` (sometimes multiple nodes: video + metadata). Here the `X` in the `/dev/videoX` is usually represented by in integer `0,1,2...` depending on the enumeration that OS does to all the cameras connected/available in the pc.

## 2) “Firmware/device info” you can read (identity + capabilities)

These are not typically “settable”; they describe what the device is and what it supports.

```bash
v4l2-ctl -d /dev/videoX --all
```

From this you typically get:

* **Driver / card / bus info** (who is driving the device, USB path)
* **Capabilities flags** (streaming, capture, etc.)
* Current format summary (sometimes)
* Current control values snapshot (depends on device)

For a cleaner identity-focused view:

```bash
v4l2-ctl -d /dev/videoX --info
```

## 3) Supported modes that the firmware advertises (what it can do)

This is the authoritative list of resolution, pixel format, and frame intervals (FPS options).

```bash
v4l2-ctl -d /dev/videoX --list-formats-ext
```

You will see entries like:

* Pixel formats: `MJPG`, `YUYV`, etc.
* Discrete sizes: 640×480, 1280×720, …
* Discrete frame intervals (e.g., 1/30, 1/60)

This is the closest thing to “camera firmware mode table”.

## 4) Parameters you can control (V4L2 controls)

List all controls, with ranges, defaults, and flags:

```bash
v4l2-ctl -d /dev/videoX -l
```

Interpretation:

* Controls that appear here are what you can *potentially* control.
* Each control shows:

  * type, min/max/step, default, current value
  * flags like **inactive**, **read-only**, **volatile**

    * **read-only**: you cannot set it
    * **inactive**: disabled because another mode is active (e.g., auto-exposure on)
    * **volatile**: may change automatically (even if you didn’t set it)

To read current values (quick snapshot):

```bash
v4l2-ctl -d /dev/videoX -C exposure_auto -C exposure_absolute -C gain
```

To set controls (example):

```bash
v4l2-ctl -d /dev/videoX -c exposure_auto=1      # 1 often means "manual" on many UVC cams; verify from -l output
v4l2-ctl -d /dev/videoX -c exposure_absolute=50
v4l2-ctl -d /dev/videoX -c gain=0
```

Important: control naming/semantics vary. Always use `-l` output as the source of truth for that specific device.

## 5) Streaming parameters you request vs what you actually get

To query streaming parameters (FPS-related):

```bash
v4l2-ctl -d /dev/videoX --get-parm
```

To set FPS request:

```bash
v4l2-ctl -d /dev/videoX --set-parm=60
```

To set format (resolution + pixel format):

```bash
v4l2-ctl -d /dev/videoX --set-fmt-video=width=1280,height=720,pixelformat=MJPG
v4l2-ctl -d /dev/videoX --get-fmt-video
```

This pair is critical: it distinguishes what you *asked for* from what the driver *negotiated*.

## 6) The clean separation you want to document

In your docs, use this taxonomy:

**A. Fixed / descriptive (device-reported)**

* Driver/card/bus info: `--info`, `--all`
* Supported formats/modes: `--list-formats-ext`
* Capabilities flags: `--info`

**B. Controllable (exposed controls)**

* Exposure/gain/white balance/focus/etc.: `-l`, `-C`, `-c`

**C. Negotiated streaming state (requested vs achieved)**

* Current format: `--get-fmt-video`
* Current frame rate parameters: `--get-parm`

## 7) What to store per run (instrument-grade habit)

In each run folder, dump:

```bash
v4l2-ctl -d /dev/videoX --info            > v4l2_info.txt
v4l2-ctl -d /dev/videoX --all             > v4l2_all.txt
v4l2-ctl -d /dev/videoX -l                > v4l2_controls.txt
v4l2-ctl -d /dev/videoX --list-formats-ext> v4l2_formats.txt
v4l2-ctl -d /dev/videoX --get-fmt-video   > v4l2_get_fmt.txt
v4l2-ctl -d /dev/videoX --get-parm        > v4l2_get_parm.txt
```

That becomes your “truth record” for reproducibility.

If you tell me your `/dev/videoX` node and (optionally) paste the output of `--list-formats-ext` and `-l`, I can recommend the best target mode (resolution/FPS/pixel format) and the exact control-lock sequence for stable measurements.

