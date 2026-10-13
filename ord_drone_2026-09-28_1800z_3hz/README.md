# ORD drone run at 3 Hz

This run covers September 28, 2026, 18:00–18:05 UTC. One Kraken drone flew from east of ORD toward the airport center. [`drone_waypoints.jsonl`](drone_waypoints.jsonl) contains its planned route. [`simulation_poses_native.jsonl`](simulation_poses_native.jsonl) contains 902 reads of its rendered position and orientation. The three cameras used the same locations and headings as the aircraft run, with level pitch and a 45° horizontal field of view.

The cameras share 897 image timestamps. Four expected 3 Hz time slots have no synchronized frame; [`sync_index.jsonl`](sync_index.jsonl) identifies the frames that were kept. The nearest drone pose read was a median of 85 ms from a selected image time and at most 695 ms away, so the pose and image rows should be joined by timestamp.

## Camera tracks

YOLO11s used its `airplane` class to detect the drone. The camera tracker produced 27 track IDs and 11,034 position rows in [`camera_tracks_native.jsonl`](camera_tracks_native.jsonl). Three IDs were matched to the drone using segmentation masks. The other 24 IDs remain in the file but did not pass the motion check. An ID without a verified match is left unmapped in [`metadata.json`](metadata.json). A missed detection can split one drone's path across multiple IDs.

The table counts drone appearances in selected frames with valid segmentation masks. A drone visible in two frames counts twice. “Extra detections” are YOLO boxes without a matching drone mask.

| Camera | Visible drone instances | YOLO matches | Misses | Extra detections |
| --- | ---: | ---: | ---: | ---: |
| Camera 1 | 24 | 23 | 1 | 1 |
| Camera 2 | 66 | 60 | 6 | 2,492 |
| Camera 3 | 16 | 16 | 0 | 0 |

Camera 2's view includes parked aircraft in the airport map, which contribute extra `airplane` detections. The `airplane` label does not identify a drone type.

For the shared file layout, coordinates, and track format, see the [repository README](../README.md).
