# ORD aircraft and drone trajectories

This dataset contains 100 five-minute scenarios near Chicago O'Hare International Airport (ORD). Each scenario combines aircraft trajectories calculated from historical ADS-B observations with one or two prescribed drone trajectories. The aircraft intervals are listed in `index.jsonl` and do not overlap the September 28–October 4 intervals used for the 800 aircraft training scenarios.

The dataset contains full trajectories at 3 Hz. The noisy positions are reference positions with Gaussian noise added to represent an approximate tracker output. No cameras, object detector or tracker produced these noisy positions.

## Files

The root contains this README, `index.jsonl` and one folder per scenario. The index retains the fields used in the aircraft-only batch; `reference_samples` counts both aircraft and drone rows. Each scenario folder contains:

| File | Contents |
| --- | --- |
| `reference_tracks_3hz.jsonl` | Aircraft and drone reference positions, orientations and velocities at 3 Hz. |
| `noisy_tracks_3hz.jsonl` | The same positions and timestamps with independent Gaussian position noise. |
| `adsb_observations.jsonl` | Original aircraft route observations at their recorded timestamps, including bracketing observations outside the five-minute interval. |
| `drone_waypoints.jsonl` | Prescribed drone positions and timestamps at 3 Hz. |
| `metadata.json` | Time interval, coordinate origin, aircraft and drone IDs, route phases, noise settings, source information and validation results. |

Each line in a JSONL file is one JSON object. `source_object_id` identifies an aircraft or drone within a scenario. Join the reference and noisy rows on `source_object_id` and `frame_index`. The noisy rows retain the reference IDs and vehicle types: this assumes perfect identity association and classification. They contain no simulated missed detections, false detections or split track IDs.

The drone reference rows use the same fields as aircraft reference rows. ADS-B-specific `source_times_utc_s`, `interpolation_fraction` and `altitude_fallback_used` are null for drones.

## Time and coordinates

`frame_index` identifies a point on the 3 Hz grid: `elapsed_s = frame_index / 3`. `utc_s` is Unix time in seconds. Aircraft have rows only where the recorded observations support a position within the airport bounds; missing intervals remain missing. Drone rows cover only the times when a drone is present.

`xyz_enu_m` gives east, north and up in metres relative to the WGS84 origin at 41.980103° N, 87.903868° W and 2,250 m altitude. The origin is also in `metadata.coordinate_frame.origin_wgs84`. Positions at nominal ground level have `z` of approximately −2,083 m. Quaternions are ordered `x,y,z,w`. Aircraft reference velocities use backward differences between adjacent 3 Hz positions; the first state after a gap has a null velocity. Noisy rows do not contain velocity or orientation.

The aircraft positions use the existing replay interpolation code. Reported geometric altitude is used when available and uncorrected barometric altitude otherwise; these are not adjusted to a common vertical datum. Missing source altitude uses 166.8 m and is flagged in the aircraft reference rows. Drone heights are prescribed relative to this same nominal ground altitude; no terrain elevation or building collision check was performed.

## Drone routes

There are 20 scenarios in each family: one crossing, two crossings, circling, approaching and hovering before departing, and approaching the control tower before hovering, circling and departing. In the two-crossing scenarios, two drones start 30 seconds apart. Half the crossing variants last one minute and span approximately 1 km. Longer single-drone crossings span approximately 7.2 km; longer two-drone crossings span approximately 2.5 km.

The tower routes use the approximate center of the mapped [Control Tower 910 footprint](https://www.openstreetmap.org/way/163500116), at 41.97597279° N, 87.90326564° W. This is a map-derived location, not a surveyed tower position. Route phases and anomaly intervals are recorded per drone in `metadata.track_ids.reference_tracks`. The evaluation label `drone_present` covers each drone's active interval; the individual phases describe what the drone does.

The drone trajectories are prescribed kinematic paths. They were not produced by a flight dynamics model or a recorded drone flight. Speed is checked against a 40 m/s limit; the actual speed depends on the route.

## Noise

Each noisy position has independent Gaussian noise added in east, north and up, with mean 0 and standard deviation 1 m on each axis. The variance is 1 m² per axis. Each scenario and object has a repeatable random sequence derived from the root seed and its ID; the exact seed rule and NumPy version are recorded in metadata.

The noisy rows are an approximation for initial experiments. They do not model a detector, camera field of view, tracking association, occlusion or tracker lifecycle. The reference and noisy files have the same rows and timestamps.

## Source

Aircraft observations come from [ADSB.lol/readsb historical data](https://www.adsb.lol/docs/open-data/historical/) under the [Open Database License 1.0](https://opendatacommons.org/licenses/odbl/1-0/). Each scenario contains the original observations used; metadata records the source archive information. Aircraft are selected for sustained airborne motion, and each scenario contains a sample of the traffic observed in its source interval.

Some source aircraft traces may be unavailable. Each scenario's `metadata.json` records failed source downloads in `source_input.archive.download_errors`; aircraft without a downloaded trace cannot appear in that scenario.
