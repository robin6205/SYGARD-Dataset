# SYGARD Dataset

Each folder contains one ORD simulation run.

- [Initial ORD aircraft run](ord_2026-09-28_1800z/README.md): the earlier five-minute, three-camera aircraft dataset.
- [ORD aircraft, 3 Hz](ord_aircraft_2026-09-28_1800z_3hz/README.md): five minutes of aircraft traffic replayed from historical ADS-B routes.
- [ORD drone, 3 Hz](ord_drone_2026-09-28_1800z_3hz/README.md): one drone flying from east of ORD toward the airport center.

## New 3 Hz runs

Both new folders contain full five-minute trajectories at their original timestamps:

| File | Contents |
| --- | --- |
| `simulation_poses_native.jsonl` | Positions read back from each rendered aircraft or drone in Unreal. These are the simulation reference tracks. |
| `camera_tracks_native.jsonl` | Estimated 3D position, velocity, time, and ID from the camera tracker. The `status` field says whether a state used a new detection or a Kalman prediction. |
| `camera_poses.jsonl` | Position and orientation of each selected camera frame. |
| `metadata.json` | Camera calibration, object IDs, and verified matches between camera track IDs and simulated object IDs. |
| `sync_index.jsonl` | Selected camera frames and their nearest actor pose readbacks for each 3 Hz time slot. |
| `simulation_truth.tfrecord` | Simulation reference tracks in Waymo Motion `Scenario` records. |
| `camera_tracks.tfrecord` | Camera tracker states in Waymo Motion `Scenario` records. |

The camera tracks are processed tracker output, not raw YOLO detections. Here **3 Hz** means actor pose reads were requested about three times per second and camera frames were selected about three times per second. Actor and camera timestamps are separate. The native JSONL files retain those timestamps without interpolation or 30-second windows. A camera track can have several rows at one image timestamp because the three camera frames were processed in sequence; `event_index` gives their order. The TFRecord files place the track data in 30-second Waymo Motion `Scenario` windows on a nominal 3 Hz grid.

Elapsed seconds start at 2026-09-28 18:00:00 UTC. The native timestamps are simulator-clock nanoseconds; `metadata.json` gives the simulator clock value at that UTC time. Positions are metres east, north, and up from 41.980103° N, 87.903868° W, 2,250 m altitude. Camera and object quaternions are stored as `x,y,z,w` and rotate local axes into this frame.

The two TFRecords have independent track IDs. Use `metadata.json` to link them to camera tracker IDs or simulated object IDs. The aircraft folder also includes the original ADS-B observations used to set its routes. The drone folder includes its prescribed route points. The instance READMEs give results specific to each run.

## Replay the tracks on a map

With Python 3.10 or newer, run the aircraft viewer from the repository root:

```powershell
python viewer/app.py --track ord_aircraft_2026-09-28_1800z_3hz
```

For the drone run:

```powershell
python viewer/app.py --track ord_drone_2026-09-28_1800z_3hz
```

The viewer prints a local URL and opens it in a browser. To run both viewers at once, add `--port 8782` to the second command. The **Camera tracks only** switch hides the Unreal reference trajectories. See the [viewer README](viewer/README.md) for the other controls. The map uses OpenStreetMap tiles and needs an internet connection, but no map API key.
