# ORD aircraft trajectory training set

This set contains 800 aircraft-only scenarios. Each scenario covers a distinct five-minute interval near ORD, drawn from 28 September through 4 October 2026. `index.jsonl` lists the folders, UTC intervals, aircraft counts and row counts.

The trajectories are calculated from historical ADS-B routes. This batch provides aircraft training trajectories without camera capture. It contains no injected anomalies or drones.

## Files

This README describes the whole dataset. `index.jsonl` lists each scenario's folder, UTC interval, aircraft count and row counts. Each scenario folder contains three files:

| File | Contents |
| --- | --- |
| `reference_tracks_3hz.jsonl` | Full calculated trajectories at 3 Hz. Each row is one aircraft state, ordered by `frame_index`, then `source_object_id`. |
| `adsb_observations.jsonl` | Original ADS-B route observations with their recorded timestamps and values. Rows are ordered by aircraft ID, then time. Bracketing observations can fall outside the five-minute interval. |
| `metadata.json` | Aircraft IDs and reported types, UTC interval, coordinate origin, source information, selection and interpolation settings, counts and validation results. |

Both JSONL files use `source_object_id`, the ADS-B aircraft identifier. Join it to `metadata.track_ids.reference_tracks[].source_object_id` for aircraft type and registration. One ID covers the aircraft's full available trajectory within the scenario, including any gaps.

## Fields and coordinates

| Field in `reference_tracks_3hz.jsonl` | Meaning |
| --- | --- |
| `source_object_id` | Aircraft ID, unchanged from the source route. |
| `vehicle_type`, `adsb_reported_type` | `aircraft` and its reported subtype, such as `B738`. An unknown subtype is null. |
| `elapsed_s`, `utc_s` | Seconds from the scenario start and Unix UTC seconds, respectively. |
| `frame_index` | Position on the 3 Hz grid: `elapsed_s = frame_index / 3`. |
| `xyz_enu_m` | Position in metres: east, north, up. |
| `velocity_enu_mps` | East, north and up velocity, calculated from adjacent 3 Hz positions. Null at track starts and after gaps. |
| `quaternion_xyzw_enu` | Orientation as `x,y,z,w`, rotating local object axes into the east, north, up frame. |
| `heading_rad` | Horizontal angle in radians, counterclockwise from east, as in the earlier bags. |
| `heading_deg` | The same heading in compass degrees, clockwise from north. |
| `latitude`, `longitude`, `altitude_m` | Calculated geographic position in degrees and metres. |
| `on_ground` | Ground status from the nearer source observation. |
| `altitude_source`, `altitude_fallback_used` | Source altitude label and whether either interpolation endpoint needed the fallback altitude. |
| `source_times_utc_s`, `interpolation_fraction` | The two original observation times and the interpolation weight used for this state. |

The coordinate origin matches the earlier ORD bags: 41.980103° N, 87.903868° W, altitude 2,250 m. It is stored in `coordinate_frame.origin_wgs84` as `latitude_deg`, `longitude_deg` and `altitude_m`. Ground-level `z` is about −2,083 m relative to this origin.

`adsb_observations.jsonl` stores observation fields directly in each row, using the same layout as the earlier aircraft bag. These include `utc_s`, `latitude`, `longitude`, `altitude_m`, `altitude_source`, `on_ground`, `speed_mps`, `heading_deg`, `vertical_speed_mps`, `roll_deg`, `callsign`, `source` and `flags`, together with the aircraft ID and type. Original values and timestamps are retained. Observation intervals are irregular; this file is not resampled to 3 Hz.

## How this batch differs from the earlier bags

The earlier `simulation_poses_native.jsonl` files contain positions read back from Unreal. Here, `reference_tracks_3hz.jsonl` contains positions calculated directly from the ADS-B routes using the replay interpolation code. The original observations remain in `adsb_observations.jsonl` for anyone who wants to choose a different sampling rate or interpolation method.

Each bag retains the full available five-minute trajectories. There are no prediction windows or TFRecords. No Unreal actor poses, camera tracks or camera poses were collected for this batch. The metadata therefore lists aircraft under `track_ids.reference_tracks`; it contains no simulator clock or camera-track ID mapping. `files` in the metadata identifies the two JSONL files.

## Interpolation and missing data

Calculated states lie on a 3 Hz grid from 0 through 300 seconds, inclusive. An aircraft has a row only when its source observations support a position inside the ORD bounds. Latitude, longitude and altitude are interpolated linearly. Gaps over 30 seconds, flagged airborne discontinuities and positions outside the configured area have no state rows. Tracks are not extended before the first or after the last observation.

Heading points toward the next route waypoint, with reported heading as a fallback. Pitch follows the route's altitude change; roll uses the reported value when available, otherwise zero. These are calculated orientations, not recorded aircraft attitudes.

Altitude uses reported geometric height when available and uncorrected barometric height otherwise. The altitude labels are retained; the heights have not been adjusted to one common vertical reference. Missing altitudes use 166.8 m and are flagged in each calculated state. No terrain elevation was queried.

## Aircraft selection

An aircraft qualifies through at least 25 seconds of sustained airborne movement near ORD, reported speed of at least 30 m/s, 1,200 m travelled, 800 m displacement and four original observations. Selection also requires height 25–1,100 m above a 166 m reference ground altitude. The complete available route of each qualifying aircraft is retained, including ground portions. A bag containing only parked aircraft, taxiing or brief appearances does not qualify.

Each scenario contains a sample of recorded traffic. Some intervals use subsets of aircraft from cached daily histories and may omit other traffic present at ORD. Metadata records the source selection scope. Climbing, descending and level labels describe altitude change; they are not verified takeoff or landing labels.

The five-minute source intervals do not overlap, and the calculated trajectory sets are distinct after ignoring aircraft IDs and absolute UTC dates. The same aircraft can continue into an adjacent scenario. Split training and evaluation by recording date to avoid putting portions of the same flight in both.

## Data source

The observations come from [ADSB.lol/readsb historical traces](https://www.adsb.lol/docs/open-data/historical/) under the [Open Database License 1.0](https://opendatacommons.org/licenses/odbl/1-0/). Each bag includes the observations used and the source URLs and identifiers in its metadata.
