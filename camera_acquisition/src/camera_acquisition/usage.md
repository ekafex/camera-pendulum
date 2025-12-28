# Using the pipeline



### Module layout

```bash
camera_acquisition/
  src/
    camera_acquisition/
      __init__.py
      types.py
      acquisition.py
      tracking.py
      pipeline.py
      logging.py
  scripts/
    run_realtime_track.py
```





```bash
python -m camera_acquisition.run_realtime_track --index 2 --out camera_acquisition/runs/track_test.csv
```



1.  **You cannot “forget” timestamps**:
    -   the tracker API requires a `FramePacket` (includes timestamps)
    -   the result must return `t_ns`, and the pipeline enforces it
2.  **Real-time and offline are the same**:
    -   offline: read stored frames and replay `(frame, t)` packets
    -   real-time: same packet stream, same tracker, same analysis
3.  **Explicit Δt becomes natural**
    -   dt is always computed from `t_i - t_{i-1}`
    -   no hidden constant-FPS assumption leaks in

