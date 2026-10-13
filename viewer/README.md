# Track viewer

This local web app replays the recorded object and camera tracks on an OpenStreetMap map. It reads the JSONL files in an ORD dataset folder. It does not run Unreal, YOLO, or the tracker.

## Run it

Python 3.10 or newer is enough. From the repository root:

```powershell
python viewer/app.py --track ord_aircraft_2026-09-28_1800z_3hz
```

For the drone run:

```powershell
python viewer/app.py --track ord_drone_2026-09-28_1800z_3hz --port 8782
```

You can also pass a native JSONL file. The app reads `metadata.json` and `camera_poses.jsonl` from the same folder:

```powershell
python viewer/app.py --track ord_aircraft_2026-09-28_1800z_3hz/simulation_poses_native.jsonl
```

To inspect a raw simulator recording before dataset export, pass its `states.jsonl` or its run folder. That folder must also contain `source_config.json`; `camera_pose_events.jsonl` supplies camera markers when present.

The command prints a local URL and opens it in your browser. Use `--no-browser` to skip opening a tab. Stop the server with Ctrl+C. The server listens only on `127.0.0.1` and does not upload track data. Browser access to OpenStreetMap tiles and the pinned Leaflet map library requires an internet connection. Neither needs an API key.

## What the map shows

- Solid paths and aircraft or drone icons show recorded Unreal object positions. The icon points in the recorded heading. If a raw log has no heading, the viewer points it along its sampled path.
- Dashed paths and diamonds show positions estimated from camera detections, depth, and the Kalman tracker. Each object ID has a color. Camera tracks with a verified object match use that object's color; unmatched camera track IDs have their own colors. Matching colors indicate the dataset's object ID mapping, not a new association made by the viewer.
- Purple pins are camera positions. Their wedges show the horizontal field of view over an illustrative 1 km distance. They do not show actual ground coverage or account for buildings.
- The slider uses elapsed simulation seconds. The displayed UTC date and time come from `metadata.json`. Icons and diamonds appear at **recorded samples only**: the app chooses the nearest sample within 0.8 seconds and does not create new track positions. Paths break when recorded samples are more than two seconds apart.

Click a path or position icon to inspect its ID and any camera track IDs matched to the same object. The **Tracks** and **Cameras** switches show or hide their map layers. **Camera area** returns to the three-camera map view; **All paths** fits every recorded object path. The viewer reads the original sample timestamps, so it also works with the older 10 Hz instance.

**Camera tracks only** hides the recorded Unreal positions and leaves the camera tracker output on the map. A camera track can contain both positions calculated from a new detection and positions predicted by the Kalman filter when no new detection was available. The `status` field in `camera_tracks_native.jsonl` distinguishes those states.

The app uses `simulation_poses_native.jsonl`, `camera_tracks_native.jsonl`, `camera_poses.jsonl`, and `metadata.json`. It does not parse the TFRecord files or load videos. Files are read once at startup; restart the command after changing the input files.
