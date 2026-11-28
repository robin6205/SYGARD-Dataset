# Surveillance problem: ORD runway crossing, rotating cameras on roofs and poles, attacker below roof height

Coordinates are local east, north, up (ENU) in metres. Origin 41.980103 N, 87.903868 W at 2250 m altitude (the same frame as the earlier SYGARD trajectory dataset), so ground is z = -2083.2 m, not 0.

## The five inputs

| Input | Where |
|---|---|
| Map | `planning_area_enu_m` in `problem.json` (1906 m x 2322 m rectangle); `handoff_map.png` |
| Building positions | `buildings_enu.json`: 219 outlines in ENU metres with heights. The 208 taller than 10 m are no-fly areas. The same buildings in longitude/latitude: `buildings_lonlat.geojson` |
| Start and goal | `scenarios` in `problem.json` |
| Attacker speed | `attacker.speed_mps` = 15 m/s, flying 10 m above ground |
| Surveillance schedule | `schedule` of each camera in `problem.json`; what each camera sees every 0.1 s in `camera_schedule_10hz.jsonl` |

Scenario runway_crossing: start at the south-east, beside runway 04R/22L (moved about 47 m off the runway onto open ground) (1255.5, -2081.5, -2073.2); goal: apron beside Concourse B, Terminal 1 (-280.0, -175.0, -2073.2).

The goal itself is never seen by any camera: no camera is within 150 m. This is intended: the cameras watch the ways in, not the goal, so the environment is not made impossible.

## Flight height and obstacles

The attacker flies a constant 10 m above ground, below the roofs (12 m and up). So it cannot fly over them: every building taller than 10 m in `buildings_enu.json` is a no-fly area (208 of 219; the 11 buildings of 3.5 m can be flown over), and the attacker keeps 2 m (`vehicle_radius_m`) clear of it. This matches last year's flat setup, where buildings were the obstacles.

## Cameras

6 cameras, on roofs and on 14 m poles in open ground (never on runways, taxiways or aprons). They do not change position; they only rotate in place. t = 0 is the attacker launch.

| Camera | Mount | Position E, N, U (m) | Looks at t = 0 | Direction | Speed | How far | One turn |
|---|---|---|---|---|---|---|---|
| camera_01 | pole | 424.9, -1306.5, -2069.2 | 345 deg | clockwise | 12 deg/s | full 360 deg turn | 30 s |
| camera_02 | pole | 774.9, -1506.5, -2069.2 | 180 deg | clockwise | 12 deg/s | full 360 deg turn | 30 s |
| camera_03 | pole | -375.1, -556.5, -2069.2 | 210 deg | clockwise | 12 deg/s | full 360 deg turn | 30 s |
| camera_04 | roof (Concourse B) | -278.1, -354.3, -2069.2 | 180 deg | clockwise | 12 deg/s | full 360 deg turn | 30 s |
| camera_05 | roof | 216.6, -337.8, -2069.2 | 60 deg | clockwise | 12 deg/s | full 360 deg turn | 30 s |
| camera_06 | pole | -325.1, -506.5, -2069.2 | 270 deg | clockwise | 12 deg/s | full 360 deg turn | 30 s |

Heading at time t = (heading at t = 0 + speed x t) mod 360, in degrees clockwise from north.

All cameras are 14 m above ground: roof cameras on masts at least 2 m above their roof, pole cameras on 14 m poles.

## What counts as seen

The attacker is seen by a camera when all three hold:

1. it is within 30 deg either side of the camera's current heading;
2. it is within 150 m horizontally;
3. the straight line from the camera to the attacker does not pass through any building. Each building is a solid block from the ground up to its height. The camera's own building counts, so its roof edge hides the ground close to that building.

`seen.py` implements this rule (plain Python). For a 2D planner, `visible_area_enu_m` in `camera_schedule_10hz.jsonl` already gives the area each camera sees at flight height every 0.1 s, and `camera_blind_areas_enu.json` gives the area each camera can never see because of buildings.

## Known limits

- Most building heights are an assumed 12 m because the map has no height for them (one published figure, the Terminal 5 concourse roof at 46 ft (14 m), suggests this is the right range). The control tower is set to 79 m (260 ft, published height to the top), not 12 m.
- Camera positions and starting headings were chosen with last year's greedy idea re-implemented: each camera's view is a no-fly area and each round keeps the camera that most lengthens the attacker's shortest route (2 m grid), skipping any that leaves no route; stop below 5 m gain. Roof sites and 14 m poles on open ground (not on runways, taxiways or aprons) were allowed. The first 2 cameras were reserved for the runway crossing (one per runway: 10L/28R, 10C/28C), so cameras also see aircraft on those runways. The detour rule gives 0 m on open ground, so each is the allowed pole site nearest where the shortest unseen route crosses that runway, first looking at the crossing. The starting headings and turn speed were not tuned for rotation. The placement is deterministic: the same inputs give the same cameras.
- Camera intrinsics and tilt in `problem.json` are only for rendering images.

## Files

`problem.json`, `buildings_enu.json`, `buildings_lonlat.geojson`, `camera_schedule_10hz.jsonl`, `camera_blind_areas_enu.json`, `seen.py`, `handoff_map.png`, `rotating_cameras.mp4` (one 30 s turn, real time).

Map data (c) OpenStreetMap contributors (ODbL).
