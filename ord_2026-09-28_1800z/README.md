# ORD simulation - camera tracks

This folder contains aircraft tracks from a five-minute simulation of Chicago O'Hare on September 28, 2026, from 18:00 to 18:05 UTC. Historical ADS-B observations set the aircraft routes. Unreal rendered the aircraft, and three fixed cameras recorded images.

There are two sets of tracks. `simulation_truth.tfrecord` follows the aircraft as they moved in the simulation, with positions reconstructed between recorded Unreal updates. `camera_tracks.tfrecord` contains estimates made from the camera images and depth data. The camera tracker did not use the reference positions or ADS-B aircraft IDs. The original ADS-B observations are provided separately.

## Files

The folder has nine files and no subfolders. Only the two `.tfrecord` files contain Waymo Motion `Scenario` records. The other files explain this ORD run; they are not part of Waymo's dataset layout. The `.jsonl` files use one JSON object per line.

| File | Contents |
| --- | --- |
| `README.md` | File descriptions, coordinates, processing steps, and known limits. |
| `simulation_truth.tfrecord` | Aircraft positions, headings, and horizontal velocities reconstructed from recorded Unreal positions at 10 Hz. |
| `camera_tracks.tfrecord` | Positions and horizontal velocities estimated from camera detections and depth. Samples without a nearby tracker output are marked invalid. |
| `metadata.json` | Coordinate origin, camera calibration, aircraft counts, reported aircraft types, and track ID mappings. |
| `camera_poses.jsonl` | The position and orientation of each camera for each of the 2,698 saved images. |
| `adsb_observations.jsonl` | ADS-B observations used to build the routes, including observations outside the five-minute interval needed for interpolation. |
| `video_index.jsonl` | The camera image timestamp for each frame of the accompanying video. |
| `tracks.png` | Top-down and 3D plots of camera tracks, nearby simulation-reference tracks, and camera locations. |
| `four_panel_synchronized_email.mp4` | Synchronized views from three cameras and a 3D camera-track plot. |

`four_panel_synchronized_email.mp4` shows the three camera views and the 3D camera-track plot at matched times. The video keeps a measured track's trail on screen while that track has been seen within the past ten seconds, then clears it. The video does not overlay simulation-reference trails. The separate `tracks.png` plot shows tracks from the full run.

## Using the track files

Each TFRecord file contains 34 Waymo `Scenario` messages in the same time order. Each message covers 9.0 seconds at 10 Hz: 91 timestamps spaced 0.1 seconds apart. `current_time_index=10` marks the end of the first second of history. Most adjacent windows share one timestamp; the final window overlaps the preceding window so the data ends at 300.0 seconds.

Compare the two files by record order and timestamp. Their track IDs are independent: the same number in the two files does not mean the same aircraft. To look up a camera track in `metadata.json`, match the Waymo `Track.id` to `track_ids.camera_tracks[].waymo_track_id`. Those IDs run from 0 to 51. The separate `tracker_id` field is the display ID used during processing and runs from 1 to 52.

The camera file includes all 52 provisional track IDs. If you want the 10 segments that passed the motion screen, select entries whose `confirmed_moving` field is true in `metadata.json`. That screen required at least five measurements over 0.3 seconds, at least 15 m of position change, and at least 8 pixels of movement within one camera. A segment is one tracker ID; one aircraft can produce several segments when its track breaks. The screen does not assign an aircraft identity.

These records follow [Waymo's `Scenario` definition](https://github.com/waymo-research/waymo-open-dataset/blob/master/src/waymo_open_dataset/protos/scenario.proto), but they are not complete Waymo driving scenes. The records contain positions and horizontal velocities. They omit `sdc_track_index`, `tracks_to_predict`, `objects_of_interest`, `map_features`, and object `length`, `width`, and `height`. Ignore the default value of `sdc_track_index`; it does not identify a self-driving car. Do not treat zero dimensions as measured aircraft sizes. A Waymo driving-scene loader may need changes to read these aircraft records correctly.

The `center_x/y/z` fields hold reconstructed Unreal actor positions in the reference file and camera-derived position estimates in the camera file. In the camera file, a 10 Hz state is valid only when a saved tracker output falls within 50 ms of that time. A valid state may be a Kalman-filter prediction made as long as five seconds after the last detection; it is not necessarily a new camera measurement. The TFRecord does not mark predictions separately from measurements. `velocity_x/y` uses east and north metres per second: finite differences in the reference file and tracker estimates in the camera file. The camera file has no observed aircraft heading.

Waymo has no airplane value in its track-type list, so these records use `TYPE_VEHICLE`. `metadata.json` gives the aircraft type reported by ADS-B for each reference track. The camera detector reports only the broad class `airplane`. Unreal rendered every aircraft with the same A319 model, whatever type ADS-B reported. These images cannot establish that the detector recognizes aircraft subtypes.

## Coordinates and camera poses

Positions use a local east, north, up frame in metres: `x` points east, `y` north, and `z` up. The WGS84 origin in `metadata.json` is 41.980103° N, 87.903868° W, at 2,250 m altitude. Because the configured origin is above the airport surface, ground-level `z` values are around −2,000 m.

Track timestamps are seconds since 18:00:00 UTC on September 28, 2026. Camera image timestamps are simulator nanoseconds; the simulator clock reads 1,010,000,000 ns at that UTC start. Use `video_index.jsonl` to find a video's image timestamp, then match it to `camera_poses.jsonl`.

Each camera pose has a translation in `xyz_enu_m` and an orientation in `quaternion_xyzw_enu`. The quaternion rotates the camera's local axes (+X forward, +Y right, +Z down) into the east, north, up frame. The intrinsics in `metadata.json` describe the saved 1920×1080 images.

## How the tracks were made

1. The replay filled ADS-B gaps of no more than 30 seconds and used the resulting routes to move aircraft in Unreal.
2. Unreal sometimes returned the same aircraft position on successive reads while the replay advanced. To make the 10 Hz reference, we removed those repeated positions and interpolated position and heading between distinct recorded positions during each continuous active period. The reference is therefore reconstructed; it is not a direct Unreal read at every 0.1-second timestamp.
3. YOLO11s searched each RGB image for airplanes at a 1,280-pixel inference size and a 0.15 confidence threshold. The camera pipeline used synchronized simulator depth to place each detection in 3D, then added Gaussian depth noise with a 1 m standard deviation (random seed 20261005). A constant-velocity Kalman filter predicted where each track would appear next. The matching step allowed extra distance ahead of a moving aircraft after a missed frame, up to 65 m, while keeping a narrower limit to the side. The filter used a 6 m measurement standard deviation, 6 m/s² acceleration noise, and a five-second track expiry.

## Known limits

This is one simulation run. The ADS-B input contained 62 aircraft. The replay selected 41 with a sampled route in the airport area and time interval; 39 produced recorded positions while active. `metadata.json` marks the other two with `has_valid_rendered_pose=false`. Traffic is uneven. Nine-second windows in the first four minutes contain one to five rendered tracks; windows near the end contain as many as 27.

The cameras miss some small aircraft. Parked aircraft built into the 3D map can trigger false detections, and one aircraft may receive several camera track IDs. Ten of the 52 camera track segments passed the motion screen. In a comparison made after tracking, 556 of 559 camera measurements on those 10 segments were within 50 m of a rendered aircraft. This count excludes gap predictions. The nearest rendered aircraft across those measurements had eight distinct IDs. This proximity check does not establish that each camera track kept the same aircraft identity. The track that crosses a 4.6-second detection gap had predicted positions up to 54 m from the rendered aircraft before detections resumed.

Reference track 30 (`ADSB_ac2567`, reported type B788) has uneven 10 Hz speed estimates because its recorded positions were sparse. Exclude it when assessing speed near the airport. Runway and tower region polygons are not included.

## Sources

The ADS-B observations come from [ADSB.lol historical data](https://www.adsb.lol/docs/open-data/historical/) under [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/). The [Waymo protobuf definition](https://github.com/waymo-research/waymo-open-dataset/blob/master/src/waymo_open_dataset/protos/scenario.proto) is published under Apache 2.0. This package uses that definition but does not include Waymo's code.
