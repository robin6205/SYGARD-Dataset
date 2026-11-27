"""Reference implementation of the 'seen' rule in problem.json (pure Python, no dependencies).

A camera sees the attacker at time t when all three hold:
  1. the attacker is within half the horizontal field of view (30 deg) either side of the camera's heading at t;
  2. the horizontal distance from camera to attacker is at most effective_range_m (150 m);
  3. the straight 3D line from the camera to the attacker does not pass through any building. Each building is a
     vertical prism: its outline from buildings_enu.json, from the ground up to its height_m. The camera's own
     building counts too (the camera is 2 m above its roof, so the roof edge hides ground close to the building).

Usage:
    import json, seen
    prob = json.load(open('problem.json')); blds = json.load(open('buildings_enu.json'))
    world = seen.World(prob, blds)
    world.seen_by('camera_01', t=4.2, point=(x, y, z))      # -> True / False
    world.seen_by_any(t=4.2, point=(x, y, z))               # -> list of camera ids that see the point
"""

import math


def heading_at(schedule, t):
    """Heading in degrees clockwise from north at time t (s) for one camera schedule."""
    sign = 1 if schedule['direction'] == 'clockwise' else -1
    if schedule['movement'] == 'full_turn':
        return (schedule['initial_heading_deg'] + sign * schedule['yaw_rate_deg_per_s'] * t) % 360
    arc = schedule['arc_deg']; centre = schedule['arc_centre_deg']
    offset0 = ((schedule['initial_heading_deg'] - centre + 180) % 360) - 180 + arc / 2
    s = (offset0 + sign * schedule['yaw_rate_deg_per_s'] * t) % (2 * arc)
    return (centre - arc / 2 + (s if s <= arc else 2 * arc - s)) % 360


def _inside(px, py, ring):
    """Even-odd point-in-polygon test; ring is a list of (x, y), closed or not."""
    inside = False
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i]; x2, y2 = ring[(i + 1) % n]
        if (y1 > py) != (y2 > py):
            xc = x1 + (py - y1) * (x2 - x1) / (y2 - y1)
            if xc > px:
                inside = not inside
    return inside


def _crossings(ax, ay, bx, by, ring):
    """Parameters s in (0, 1) where segment a->b crosses an edge of ring."""
    out = []
    dx, dy = bx - ax, by - ay
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i]; x2, y2 = ring[(i + 1) % n]
        ex, ey = x2 - x1, y2 - y1
        den = dx * ey - dy * ex
        if abs(den) < 1e-12:
            continue
        s = ((x1 - ax) * ey - (y1 - ay) * ex) / den
        u = ((x1 - ax) * dy - (y1 - ay) * dx) / den
        if 0 < s < 1 and -1e-12 <= u <= 1 + 1e-12:
            out.append(s)
    return out


def line_blocked(cam, pt, buildings, ground_z):
    """True if the 3D segment cam -> pt passes through any building prism (z below ground_z + height_m)."""
    ax, ay, az = cam; bx, by, bz = pt
    lo_x, hi_x = min(ax, bx), max(ax, bx); lo_y, hi_y = min(ay, by), max(ay, by)
    for ring, top, (x0, y0, x1, y1) in buildings:
        if x1 < lo_x or x0 > hi_x or y1 < lo_y or y0 > hi_y:
            continue
        cuts = sorted([0.0, 1.0] + _crossings(ax, ay, bx, by, ring))
        for s0, s1 in zip(cuts[:-1], cuts[1:]):
            if s1 - s0 < 1e-12:
                continue
            m = (s0 + s1) / 2
            if _inside(ax + m * (bx - ax), ay + m * (by - ay), ring):
                z_low = min(az + s0 * (bz - az), az + s1 * (bz - az))
                if z_low < top:
                    return True
    return False


class World:
    def __init__(self, problem, buildings_fc):
        self.ground_z = problem['coordinate_frame']['ground_z_enu_m']
        self.cameras = {c['id']: c for c in problem['cameras']}
        self.buildings = []
        for f in buildings_fc['features']:
            ring = [tuple(p) for p in f['geometry']['coordinates'][0]]
            if ring[0] == ring[-1]:
                ring = ring[:-1]
            xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
            self.buildings.append((ring, self.ground_z + f['properties']['height_m'], (min(xs), min(ys), max(xs), max(ys))))

    def seen_by(self, camera_id, t, point):
        c = self.cameras[camera_id]
        cx, cy, cz = c['position_enu_m']; px, py = point[0], point[1]
        if math.hypot(px - cx, py - cy) > c['effective_range_m']:
            return False
        bearing = math.degrees(math.atan2(px - cx, py - cy)) % 360
        if abs((bearing - heading_at(c['schedule'], t) + 180) % 360 - 180) > c['horizontal_fov_deg'] / 2:
            return False
        return not line_blocked((cx, cy, cz), tuple(point), self.buildings, self.ground_z)

    def seen_by_any(self, t, point):
        return [cid for cid in self.cameras if self.seen_by(cid, t, point)]
