# Drone paths: ORD runway-crossing scenario

These are two attacker drone paths for the SYGARD scenario `ord_runway_crossing_10m` (commit `ba529e5`, scenario `runway_crossing`). Both start south-east of the south runways, cross them, and end on the apron beside Concourse B.

| File | Path | Duration | Length | Seen by cameras |
|---|---|---|---|---|
| `shortest.json` | Shortest route around the buildings at 15 m/s (reference) | 181.9 s | 2729 m | 17.5 s (Camera 1: 3.0 s, Camera 3: 14.5 s) |
| `worst_case.json` | Worst-case ingress: optimized against the known camera schedule | 274.8 s | 3509 m | 0 s |

## Frame and time

- **Coordinates.** Positions are in the dataset's ENU frame, in metres. The origin is 41.980103 N, 87.903868 W, at 2250 m altitude. This is the frame of `problem.json`.
- **Height.** The drone flies at a constant 10 m above ground, so `up_m` = −2073.2 m everywhere. Ground is at −2083.2 m.
- **Time.** `t_s` = 0 is the launch. It uses the same clock as the dataset's camera schedule.

## Fields

- `samples`: positions every 0.1 s, plus the final time.
  - `t_s`, `east_m`, `north_m`, `up_m`.
  - `seen_by`: the cameras that see the drone at that instant.
- `waypoints`: the planner's points. The path is a straight line between consecutive waypoints. `shortest.json` has 3 waypoints (start, one corner, goal); `worst_case.json` has 1146.
- `summary`: duration, length, maximum speed, closest distance to a building, and seen time and intervals per camera.
- `frame`, `time`, `seen_rule`, `dataset`: metadata.

"Seen" follows the dataset's rule. A camera sees the drone when all three hold:

- the drone is within ±30° of the camera heading;
- it is within 150 m horizontally;
- no building blocks the line of sight.

The seen times and intervals in `summary` were checked every 1 ms.

## Constraints and assumptions

- **Dataset limits.** Both paths respect the dataset's limits:
  - speed ≤ 15 m/s;
  - at least 2 m from every building taller than 10 m. The closest approach is 4.4 m for the shortest path and 5.1 m for the worst case.
- **Shortest path.** It turns instantly at its one corner. It is a geometric reference, not a flyable trajectory.
- **Worst-case path: our assumptions.** The dataset does not set any of these:
  - The drone knows the camera positions and rotation schedule exactly.
  - Acceleration is at most 2.5 m/s². The start and end velocities are free.
  - The flight time is at most 1.5 × the shortest flight time (1.5 × 183.2 s = 274.8 s). The worst case uses the full 274.8 s.
  - The drone stays inside the planning area. It comes within 3.9 m of the west edge (x = −500 m).
- **Sensitivity.**
  - At t ≈ 55 s the worst-case path passes 18 m from Camera 2. At that moment it is about 8° outside the camera's field of view, which is about 0.7 s of rotation. A small timing change can make it visible.
  - Its closest approach to Camera 3's field of view is about 13° (about 1.1 s).
- **Tracking.** The worst-case path is never in any camera's view, so an image-based tracker will not produce a track for it.
