# ORD simulation - camera tracks

This dataset covers September 28, 2026, 18:00–18:05 UTC at Chicago O'Hare. Historical ADS-B observations supplied aircraft routes. Unreal rendered the replay, and three fixed cameras recorded 2,698 images.

The files contain two kinds of tracks: aircraft positions reconstructed from the recorded simulation and positions estimated from the camera images. The camera tracker did not use the simulation positions or ADS-B identities.

## Files

This folder contains nine files. The JSONL files have one JSON object per line.

| File | Contents |
| --- | --- |
| `README.md` | File definitions, coordinates, methods, and limits. |
| `simulation_truth.tfrecord` | Simulated aircraft positions, headings, and horizontal velocities at 10 Hz. |
| `camera_tracks.tfrecord` | Camera-derived 3D positions and horizontal velocities at 10 Hz. Missing states are marked invalid. |
| `metadata.json` | Coordinate origin, camera calibration, aircraft counts and types, and track ID mappings. |
| `camera_poses.jsonl` | Position and orientation for each of the 2,698 camera images. |
| `adsb_observations.jsonl` | ADS-B input observations, including points outside the five-minute interval used to interpolate routes. |
| `video_index.jsonl` | Image timestamps for the 898 frames of the accompanying video. |
| `four_panel_synchronized_email.mp4` | Synchronized camera views and a 3D camera-track plot. |
| `tracks.png` | Top-down and 3D plots of camera tracks, nearby simulated tracks, and camera locations. |

The accompanying `four_panel_synchronized_email.mp4` shows the three camera views and a 3D camera-track plot at matched times. The plot clears a track ten seconds after its last measurement. `tracks.png` shows the full run.

## Track records

Each TFRecord has 34 Waymo Motion `Scenario` messages. Each message has 91 timestamps at 0.1-second intervals and covers 9.0 seconds. Most adjacent messages share one timestamp; the final message overlaps the previous one to end at 300.0 seconds. `current_time_index` is 10.

The two files use independent track IDs. In `metadata.json`, `track_ids.camera_tracks[].waymo_track_id` matches `Track.id` in `camera_tracks.tfrecord`. These IDs are 0–51; the processing and video IDs (`tracker_id`) are 1–52. A camera ID does not identify an ADS-B aircraft.

All 52 camera IDs are included. Ten passed the motion check (`confirmed_moving=true` in `metadata.json`). That check required at least five detections spanning 0.3 seconds, 15 m of net 3D movement, and 8 pixels of net movement in one camera. One aircraft can produce multiple IDs if the tracker loses it.

A camera state is valid when a tracker output falls within 50 ms of its 10 Hz timestamp. The output may be a Kalman prediction for up to five seconds after the last detection. The TFRecord does not distinguish predictions from new measurements. Reference positions were reconstructed between distinct Unreal actor poses; they are not direct Unreal reads at every 0.1-second timestamp.

The records contain `center_x/y/z` and `velocity_x/y`. The reference records also contain heading. Camera headings and object dimensions are unset. The Waymo type is `TYPE_VEHICLE` because its enum has no aircraft value. ADS-B-reported aircraft types are in `metadata.json`; the camera detector reports only `airplane`. Every aircraft in this replay used the same A319 visual model, so camera images cannot establish subtype accuracy.

The following Waymo fields are unset: `sdc_track_index`, `tracks_to_predict`, `objects_of_interest`, and `map_features`. Ignore the protobuf default `sdc_track_index=0`; no track was assigned that role.

## Coordinates and timing

Positions use local east, north, up coordinates in metres: x=east, y=north, z=up. The WGS84 origin is 41.980103° N, 87.903868° W, altitude 2,250 m. Ground-level z is roughly −2,000 m because the origin is above the airport.

Track times are seconds since September 28, 2026, 18:00:00 UTC. Camera image times use simulator nanoseconds; the simulator clock was 1,010,000,000 ns at that UTC start. Match `video_index.jsonl` timestamps to `camera_poses.jsonl` to find poses for video frames.

Camera poses contain `xyz_enu_m` and `quaternion_xyzw_enu`. The quaternion maps the camera's local axes (+X forward, +Y right, +Z down) into east, north, up. Camera intrinsics for the saved 1920×1080 images are in `metadata.json`.

## Generation

1. The replay interpolated ADS-B gaps of no more than 30 seconds and moved aircraft along those routes in Unreal.
2. The reference track interpolates position and heading between distinct recorded actor poses during each continuous active period.
3. YOLO11s detected airplanes in RGB images at 1,280-pixel inference size with a 0.15 confidence threshold. Synchronized simulator depth placed each detection in 3D. The depth estimate used the 25th percentile in the center 40% of its box, plus Gaussian noise with 1 m standard deviation (seed 20261005). A constant-velocity Kalman filter used 6 m measurement noise and 6 m/s² acceleration noise. Association allowed up to 65 m ahead of a moving track, with a narrower side limit; a track expired after five seconds without a detection.

## Limits

The ADS-B input contained 62 aircraft. The replay selected 41 for this area and interval; 39 had recorded positions while active. The other two are marked `has_valid_rendered_pose=false` in `metadata.json`. Traffic is sparse in the first four minutes: each nine-second reference window contains one to five aircraft, versus up to 27 near the end.

Small aircraft are sometimes missed. Parked aircraft built into the map can cause false detections. Of 559 measurements on the ten camera segments that passed the motion check, 556 were within 50 m of the nearest simulated aircraft. Gap predictions are excluded from that count. The nearest aircraft across those measurements had eight distinct IDs, but proximity does not prove a camera track kept one aircraft identity. During one 4.6-second detection gap, predicted positions were up to 54 m from the simulated aircraft.

Reference track 30 (`ADSB_ac2567`, reported type B788) has unstable 10 Hz speed estimates because its recorded positions were sparse. Runway and tower region polygons are not included.

## Sources

ADS-B observations: [ADSB.lol historical data](https://www.adsb.lol/docs/open-data/historical/), [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/). Track format: [Waymo Motion `Scenario` protobuf](https://github.com/waymo-research/waymo-open-dataset/blob/master/src/waymo_open_dataset/protos/scenario.proto), Apache 2.0.
