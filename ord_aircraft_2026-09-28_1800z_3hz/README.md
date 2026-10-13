# ORD aircraft tracks at 3 Hz

This folder covers September 28, 2026, 18:00–18:05 UTC. It contains 39 rendered aircraft objects, 3,422 active simulator pose reads, and 897 image times shared by three fixed 1280×720 cameras. The 3 Hz camera selection has 4 missing time slots; `sync_index.jsonl` lists the retained frames and the nearest actor readback for each one.

The full trajectories are in `simulation_poses_native.jsonl` and `camera_tracks_native.jsonl` at their original readback and image timestamps. Aircraft poses were recorded at 3 Hz; camera frames were selected at 3 Hz. The camera tracks contain processed 3D tracker states, including Kalman predictions between detections. The two streams were not sampled at identical instants.

## Files

Each JSONL file has one JSON object per line. The video used to inspect this run is supplied separately.

| File | Contents |
| --- | --- |
| `README.md` | File definitions, coordinates, timing, and methods. |
| `metadata.json` | Object IDs, camera calibration, simulator clock origin, and any camera track IDs matched to rendered objects. |
| `simulation_poses_native.jsonl` | Full active rendered-object tracks at the original actor readback timestamps. No interpolation or windows. |
| `camera_tracks_native.jsonl` | Full camera tracker states at the original image timestamps. `status` says whether a state used a new detection or a Kalman prediction. |
| `camera_poses.jsonl` | Position and orientation of each selected camera frame. |
| `sync_index.jsonl` | The common camera timestamp chosen for each 3 Hz time slot, its original frame sequence in each camera, and the nearest actor readback time. |
| `adsb_observations.jsonl` | Original ADS-B observations for the aircraft selected for replay. |
| `simulation_truth.tfrecord` | Waymo Motion `Scenario` messages with 91 nominal 3 Hz times each. The actor states come from nearby original reads. |
| `camera_tracks.tfrecord` | Waymo Motion `Scenario` messages with 91 nominal 3 Hz times each. Camera tracker states are assigned to those times. |

## Time and coordinates

Elapsed seconds start at 2026-09-28 18:00:00 UTC. Camera and actor timestamps are simulator-clock nanoseconds. `metadata.json` gives the simulator clock value at the UTC start. Positions use a local east, north, up frame in metres. The WGS84 origin is 41.980103° N, 87.903868° W, altitude 2,250 m; ground-level `z` is about −2,000 m. Quaternions in the JSONL files are `x,y,z,w` and rotate local object or camera axes into this east, north, up frame.

Rendered-object poses were read at a requested interval of 1/3 second. Unreal moved the objects continuously between route points. The cameras requested frames every 0.2 seconds to allow for missed renders. We kept one original three-camera frame within 1/6 second of each 3 Hz time point. The cameras share each selected image timestamp exactly. Actor pose reads are separate: their median distance from the nearest selected image time was 80.0 ms, and their maximum was 250.0 ms. Join by timestamps; do not treat the nearest actor row as a simultaneous camera measurement.

The native JSONL files preserve the measured timestamps and the full five-minute tracks. The TFRecords split the same interval into 30-second windows with 91 times each; adjacent windows share one time. Windows with no tracks are omitted. The TFRecords place nearby states on a nominal 3 Hz grid. A missing state has `valid=false`. The TFRecord camera states do not distinguish new measurements from Kalman predictions; use `status` in `camera_tracks_native.jsonl` for that.

The two TFRecords have independent track IDs; join a track ID only through the corresponding section of `metadata.json`. The `Scenario` type is `TYPE_VEHICLE` because the protobuf enum has no aircraft or drone category. Object box dimensions, `map_features`, and `tracks_to_predict` are unset, and no self-driving-car track was assigned. The protobuf default for `sdc_track_index` must be ignored.

In `metadata.json`, `track_ids.simulation_truth[].waymo_track_id` identifies a rendered object. `track_ids.camera_tracks[].waymo_track_id` identifies a camera track; its processing `tracker_id` is one greater. `matched_source_object_id` names the ADS-B aircraft when segmentation verified the match. It is null when no match was verified. Several camera track IDs can name the same object.

## How the tracks were made

Historical ADS-B observations set the aircraft routes. Unreal replayed them with the same A319 visual body for every aircraft. The rendered pose reads are the simulation reference tracks. ADS-B-reported aircraft types are retained in `metadata.json`; the images do not verify those subtypes.

YOLO11s processed each selected RGB frame using its COCO `airplane` class at a 0.15 confidence threshold and 960-pixel inference size. For each detection, the tracker used the matching simulator depth image and camera pose to estimate a 3D point. It added Gaussian depth noise with 1 m standard deviation, then used a constant-velocity Kalman filter with 6 m measurement noise, 6 m/s² acceleration noise, and a five-second expiry after the last detection. Segmentation masks were used afterward to evaluate detections and to label camera track IDs; the tracker did not receive rendered-object identities.

The camera tracker produced 16 IDs and 1,921 state rows. 14 IDs had at least two segmentation matches to one rendered object and no match to another. An unmapped ID means that this test did not verify its identity. A missed detection can start a second ID for the same object. `confirmed_moving` requires at least five detections over 0.3 seconds, 15 m of net 3D displacement, and 8 pixels of net displacement in one camera. The detector's `airplane` class is not an aircraft subtype or a drone classifier.

Segmentation check for the selected camera frames:

| Camera | Visible rendered objects | YOLO matches | Misses | Extra detections |
| --- | ---: | ---: | ---: | ---: |
| Camera 1 | 163 | 105 | 58 | 0 |
| Camera 2 | 458 | 88 | 370 | 1 |
| Camera 3 | 238 | 126 | 112 | 6 |

Only frames with a valid segmentation image contribute to these counts. An object is counted separately in each frame where it is visible.

## Data source

ADS-B observations came from [ADSB.lol historical data](https://www.adsb.lol/docs/open-data/historical/) under the [Open Database License 1.0](https://opendatacommons.org/licenses/odbl/1-0/).
