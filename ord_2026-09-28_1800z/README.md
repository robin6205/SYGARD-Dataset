# ORD simulation - camera tracks

This dataset covers September 28, 2026, 18:00–18:05 UTC at the Chicago O'Hare airport. Historical ADS-B observations supplied aircraft routes. Unreal rendered the replay, and three fixed cameras recorded 2,698 images.

The files contain two kinds of tracks: aircraft positions reconstructed from the recorded simulation and positions estimated from the detections from camera images. 

## Files

This folder contains nine files. The JSONL files have one JSON object per line.

| File | Contents |
| --- | --- |
| `README.md` | File definitions, coordinates, methods, and limits. |
| `simulation_truth.tfrecord` | Simulated aircraft positions, headings, and horizontal velocities at 10 Hz. |
| `camera_tracks.tfrecord` | Camera-derived 3D positions and horizontal velocities at 10 Hz. Missing states are marked invalid. |
| `metadata.json` | Coordinate origin, camera calibration, aircraft counts and types, and verified camera track-to-aircraft matches. |
| `camera_poses.jsonl` | Position and orientation for each of the 2,698 camera images. |
| `simulation_poses_native.jsonl` | Every recorded active Unreal actor pose, with its original readback timestamp. No interpolation or scenario windows. |
| `camera_tracks_native.jsonl` | Camera tracker states at their original image timestamps, including measured and predicted states. No 10 Hz time bins or scenario windows. |
| `adsb_observations.jsonl` | ADS-B input observations, including points outside the five-minute interval used to interpolate routes. |
| `tracks.png` | Top-down and 3D plots of camera tracks, nearby simulated tracks, and camera locations. |

## Track records

Each TFRecord has 34 Waymo Motion `Scenario` messages. Each message has 91 timestamps at 0.1-second intervals and covers 9.0 seconds. Most adjacent messages share one timestamp; the final message overlaps the previous one to end at 300.0 seconds. `current_time_index` is 10.

The two files use independent track IDs. In `metadata.json`, `track_ids.camera_tracks[].waymo_track_id` matches `Track.id` in `camera_tracks.tfrecord`. These IDs are 0–51; the tracker IDs used during processing (`tracker_id`) are 1–52. A camera ID alone does not identify an ADS-B aircraft.

All 52 camera IDs are included. Ten passed the motion check (`confirmed_moving=true` in `metadata.json`). That check required at least five detections spanning 0.3 seconds, 15 m of net 3D movement, and 8 pixels of net movement in one camera. One aircraft can produce multiple IDs if the tracker loses it.

A camera state is valid when a tracker output falls within 50 ms of its 10 Hz timestamp. The output may be a Kalman prediction for up to five seconds after the last detection. The TFRecord does not distinguish predictions from new measurements. Reference positions were reconstructed between distinct Unreal actor poses; they are not direct Unreal reads at every 0.1-second timestamp.

The records contain `center_x/y/z` and `velocity_x/y`. The reference records also contain heading. Camera headings and object dimensions are unset. The Waymo type is `TYPE_VEHICLE` because its enum has no aircraft value. ADS-B-reported aircraft types are in `metadata.json`; the camera detector reports only `airplane`. Every aircraft in this replay used the same A319 visual model, so camera images cannot establish subtype accuracy.

The following Waymo fields are unset: `sdc_track_index`, `tracks_to_predict`, `objects_of_interest`, and `map_features`. Ignore the protobuf default `sdc_track_index=0`; no track was assigned that role.

## Full trajectories and original timestamps

The two native JSONL files cover the full five-minute run without splitting tracks into scenarios. Each line is one state, and rows are sorted by track ID and timestamp. `waymo_track_id` joins each file to the corresponding TFRecord and to `metadata.json`. An aircraft has rows only while it is active; a camera track has rows only while the tracker maintains it. Keep gaps when choosing your own history lengths and prediction horizons.

`simulation_poses_native.jsonl` has 11,272 active actor pose readbacks from 3,002 simulator snapshots. The snapshots were irregular, with a median interval of 0.10 s. Repeated positions are retained. Distinct pose values typically appeared about 0.30 s apart; the exact Unreal movement update times were not recorded. Each row has the actor name, ADS-B address (`icao24`), simulator timestamp, elapsed seconds, position, orientation, and heading. The final readback is at 300.1 s; the TFRecords stop at 300.0 s.

`camera_tracks_native.jsonl` has 7,367 tracker state rows from the 2,698 camera frame events. Each camera captured about three frames per second (median interval 0.33 s). A row has its exact image timestamp, camera and frame IDs, position, velocity, uncertainty, and `status` (`measured` or `predicted`). Cameras can record events at the same timestamp, so a track may have multiple rows with that timestamp; `event_index` preserves their processing order. The 10 Hz camera TFRecord instead assigns states to nearby grid times and marks the other times invalid.

The `track_ids.camera_tracks` entries in `metadata.json` now include `matched_actor_name`, `matched_icao24`, `segmentation_match_count`, and `detection_count`. These are post-processing labels: a tracked YOLO detection was matched to a spawned aircraft's synchronized segmentation mask. The tracker did not receive these identities. All ten camera IDs that passed the motion check matched eight spawned aircraft; the other 42 have null aircraft IDs. A null ID means no verified match, not proof that the detection was false. Tracker IDs 27, 32, and 33 each match aircraft `a2479f` (Waymo camera track IDs 26, 31, and 32).

## Coordinates and timing

Positions use local east, north, up coordinates in metres: x=east, y=north, z=up. The WGS84 origin is 41.980103° N, 87.903868° W, altitude 2,250 m. Ground-level z is roughly −2,000 m because the origin is above the airport.

Track times are seconds since September 28, 2026, 18:00:00 UTC. Camera image times use simulator nanoseconds; the simulator clock was 1,010,000,000 ns at that UTC start. Image timestamps are in `camera_poses.jsonl`.

Camera poses contain `xyz_enu_m` and `quaternion_xyzw_enu`. The quaternion maps the camera's local axes (+X forward, +Y right, +Z down) into east, north, up. Camera intrinsics for the saved 1920×1080 images are in `metadata.json`.

## Generation

1. The replay interpolated ADS-B gaps of no more than 30 seconds and moved aircraft along those routes in Unreal.
2. The reference track interpolates position and heading between distinct recorded actor poses during each continuous active period.
3. YOLO11s detected airplanes in RGB images at 1,280-pixel inference size with a 0.15 confidence threshold. Synchronized simulator depth placed each detection in 3D. The depth estimate used the 25th percentile in the center 40% of its box, plus Gaussian noise with 1 m standard deviation (seed 20261005). A constant-velocity Kalman filter used 6 m measurement noise and 6 m/s² acceleration noise. Association allowed up to 65 m ahead of a moving track, with a narrower side limit; a track expired after five seconds without a detection.

## Limits and TODO

The ADS-B input contained 62 aircraft. The replay selected 41 for this area and interval; 39 had recorded positions while active. The other two are marked `has_valid_rendered_pose=false` in `metadata.json`. Traffic is sparse in the first four minutes: each nine-second reference window contains one to five aircraft, versus up to 27 near the end.

Small aircraft are sometimes missed. Parked aircraft built into the map can cause false detections. Of 559 measurements on the ten camera segments that passed the motion check, 556 were within 50 m of the nearest simulated aircraft. Gap predictions are excluded from that count. The nearest aircraft across those measurements had eight distinct IDs, but proximity does not prove a camera track kept one aircraft identity. During one 4.6-second detection gap, predicted positions were up to 54 m from the simulated aircraft.

Reference track 30 (`ADSB_ac2567`, reported type B788) has unstable 10 Hz speed estimates because its recorded positions were sparse. Runway and tower region polygons are not included yet.

## Sources

ADS-B observations: [ADSB.lol historical data](https://www.adsb.lol/docs/open-data/historical/), [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/). Track format: [Waymo Motion `Scenario` protobuf](https://github.com/waymo-research/waymo-open-dataset/blob/master/src/waymo_open_dataset/protos/scenario.proto).
