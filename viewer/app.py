"""Serve an ORD track dataset as a local, read-only map replay."""

from __future__ import annotations

import argparse
import json
import math
import sys
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


HERE = Path(__file__).resolve().parent
NATIVE_FILES = ("simulation_poses_native.jsonl", "camera_tracks_native.jsonl")


def read_jsonl(path: Path):
    with path.open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            if line.strip():
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as error:
                    raise ValueError(f"{path.name}:{number}: {error.msg}") from error


def ecef(latitude, longitude, altitude):
    lat, lon = map(math.radians, (latitude, longitude))
    eccentricity = 0.0066943799901413165
    radius = 6378137 / math.sqrt(1 - eccentricity * math.sin(lat) ** 2)
    return ((radius + altitude) * math.cos(lat) * math.cos(lon),
            (radius + altitude) * math.cos(lat) * math.sin(lon),
            (radius * (1 - eccentricity) + altitude) * math.sin(lat))


def enu_to_wgs84(xyz, origin):
    """Convert local east/north/up metres using the WGS84 ellipsoid."""
    east, north, up = map(float, xyz)
    lat = math.radians(origin["latitude_deg"])
    lon = math.radians(origin["longitude_deg"])
    ref = ecef(origin["latitude_deg"], origin["longitude_deg"], origin["altitude_m"])
    dx = -math.sin(lon) * east - math.sin(lat) * math.cos(lon) * north + math.cos(lat) * math.cos(lon) * up
    dy = math.cos(lon) * east - math.sin(lat) * math.sin(lon) * north + math.cos(lat) * math.sin(lon) * up
    dz = math.cos(lat) * north + math.sin(lat) * up
    x, y, z = (ref[0] + dx, ref[1] + dy, ref[2] + dz)
    longitude = math.atan2(y, x)
    p = math.hypot(x, y)
    latitude = math.atan2(z, p * (1 - 0.0066943799901413165))
    for _ in range(7):
        sine = math.sin(latitude)
        radius = 6378137 / math.sqrt(1 - 0.0066943799901413165 * sine * sine)
        altitude = p / math.cos(latitude) - radius
        latitude = math.atan2(z, p * (1 - 0.0066943799901413165 * radius / (radius + altitude)))
    return [round(math.degrees(latitude), 8), round(math.degrees(longitude), 8), round(altitude, 2)]


def camera_direction(quaternion):
    """The exported camera's local +X axis points forward."""
    x, y, z, w = map(float, quaternion)
    norm = math.sqrt(x * x + y * y + z * z + w * w)
    x, y, z, w = (value / norm for value in (x, y, z, w))
    east = 1 - 2 * (y * y + z * z)
    north = 2 * (x * y + z * w)
    up = 2 * (x * z - y * w)
    return [round(math.degrees(math.atan2(east, north)) % 360, 2),
            round(math.degrees(math.atan2(up, math.hypot(east, north))), 2)]


def start_utc(metadata):
    interval = metadata.get("interval_utc") or []
    if interval:
        return interval[0]
    return metadata.get("start_utc")


def source_id(row):
    return str(row.get("source_object_id") or row.get("icao24") or row.get("actor_name") or row.get("id") or row.get("waymo_track_id", "unknown"))


def add_native_tracks(path, kind, origin, metadata, tracks):
    names = metadata.get("track_ids", {}).get("simulation_truth" if kind == "reference" else "camera_tracks", [])
    by_waymo = {entry.get("waymo_track_id"): entry for entry in names}
    for row in read_jsonl(path):
        xyz = row.get("xyz_enu_m")
        if not isinstance(xyz, list) or len(xyz) != 3:
            continue
        track_id = row.get("waymo_track_id", row.get("tracker_id"))
        key = f"{kind}:{track_id}"
        info = by_waymo.get(row.get("waymo_track_id"), {})
        matched = row.get("matched_source_object_id") or info.get("matched_source_object_id")
        label = source_id(row) if kind == "reference" else f"Camera track {row.get('tracker_id', info.get('tracker_id', track_id))}"
        track = tracks.setdefault(key, {"key": key, "kind": kind, "label": label,
                                        "object_id": source_id(row) if kind == "reference" else matched,
                                        "vehicle_type": row.get("vehicle_type") or info.get("vehicle_type"),
                                        "camera_match": matched,
                                        "confirmed_moving": bool(row.get("confirmed_moving", info.get("confirmed_moving", False))),
                                        "samples": []})
        if kind == "sensor" and row.get("confirmed_moving"):
            track["confirmed_moving"] = True
        lat, lon, altitude = enu_to_wgs84(xyz, origin)
        heading_rad = row.get("heading_rad") if kind == "reference" else None
        heading_deg = ((90 - math.degrees(heading_rad)) % 360
                       if isinstance(heading_rad, (int, float)) and math.isfinite(heading_rad) else None)
        track["samples"].append([round(float(row["elapsed_s"]), 3), lat, lon, altitude,
                                 row.get("status", "recorded"), heading_deg])


def add_cameras(path, origin, metadata, cameras):
    intrinsics = metadata.get("camera_intrinsics", {})
    for row in read_jsonl(path):
        xyz, quaternion = row.get("xyz_enu_m"), row.get("quaternion_xyzw_enu")
        if not xyz or not quaternion:
            continue
        camera_id = str(row["camera_id"])
        info = intrinsics.get(camera_id, {})
        camera = cameras.setdefault(camera_id, {"id": camera_id, "name": info.get("name", camera_id),
                                                "fov_deg": info.get("horizontal_fov_deg", 70), "samples": []})
        lat, lon, altitude = enu_to_wgs84(xyz, origin)
        heading, pitch = camera_direction(quaternion)
        camera["samples"].append([round(float(row["elapsed_s"]), 3), lat, lon, altitude, heading, pitch])


def add_raw_states(path, origin, tracks):
    config = json.loads((path.parent / "source_config.json").read_text(encoding="utf-8"))
    first_utc = float(config["start_utc_s"])
    start_ns = None
    for frame in read_jsonl(path):
        if start_ns is None:
            start_ns = round(float(frame["sim_clock_ns"]) - float(frame["elapsed_s"]) * 1e9)
        elapsed = float(frame.get("elapsed_s", float(frame["utc_s"]) - first_utc))
        for agent in frame.get("agents", []):
            if not agent.get("active") or agent.get("render_transition_excluded"):
                continue
            translation = (agent.get("actual_pose") or {}).get("translation")
            if not translation:
                continue
            xyz = [translation["x"], -translation["y"], -translation["z"]]
            if not all(math.isfinite(value) and abs(value) < 50000 for value in xyz):
                continue
            object_id = str(agent.get("icao24") or agent.get("actor_name") or "unknown")
            key = f"reference:{object_id}"
            track = tracks.setdefault(key, {"key": key, "kind": "reference", "label": object_id,
                                            "object_id": object_id,
                                            "vehicle_type": agent.get("actual_aircraft_type"),
                                            "camera_match": None, "confirmed_moving": True, "samples": []})
            lat, lon, altitude = enu_to_wgs84(xyz, origin)
            track["samples"].append([round(elapsed, 3), lat, lon, altitude, "recorded", None])
    return start_ns


def add_raw_cameras(path, origin, start_ns, cameras):
    if not path.exists():
        return
    for row in read_jsonl(path):
        planned = row.get("planned", {})
        translation = (row.get("actual_pose") or {}).get("translation")
        if not translation:
            continue
        camera_id = str(row.get("id") or planned.get("id"))
        camera = cameras.setdefault(camera_id, {"id": camera_id, "name": planned.get("name", camera_id),
                                                "fov_deg": planned.get("fov_deg", 70), "samples": []})
        lat, lon, altitude = enu_to_wgs84([translation["x"], -translation["y"], -translation["z"]], origin)
        camera["samples"].append([round((row["sim_time_ns"] - start_ns) / 1e9, 3), lat, lon, altitude,
                                  planned.get("heading_deg", 0), planned.get("pitch_deg", 0)])


def load_dataset(selected: Path):
    selected = selected.expanduser().absolute()
    if not selected.exists():
        raise ValueError(f"Input does not exist: {selected}")
    if selected.is_dir():
        folder, selected_file = selected, None
    elif selected.is_file():
        folder, selected_file = selected.parent, selected.name
    else:
        raise ValueError("--track must name a dataset folder or JSONL file")
    supported_files = set(NATIVE_FILES) | {"metadata.json", "camera_poses.jsonl", "states.jsonl"}
    if selected_file and selected_file not in supported_files:
        raise ValueError(f"Unsupported track file: {selected_file}. Pass a dataset folder, native track JSONL, or states.jsonl")

    raw = (selected_file == "states.jsonl" or selected_file is None and
           (folder / "states.jsonl").exists() and not (folder / "metadata.json").exists())
    tracks, cameras = {}, {}
    if raw:
        if not (folder / "source_config.json").exists():
            raise ValueError("states.jsonl needs source_config.json in the same folder")
        config = json.loads((folder / "source_config.json").read_text(encoding="utf-8"))
        source_origin = config["origin"]
        origin = {"latitude_deg": source_origin["latitude"], "longitude_deg": source_origin["longitude"],
                  "altitude_m": source_origin["altitude"]}
        start_ns = add_raw_states(folder / "states.jsonl", origin, tracks)
        add_raw_cameras(folder / "camera_pose_events.jsonl", origin, start_ns, cameras)
        utc = config.get("start_utc")
        title = folder.name
    else:
        metadata_path = folder / "metadata.json"
        if not metadata_path.exists():
            raise ValueError("A native JSONL file needs metadata.json beside it; pass a dataset folder or states.jsonl")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        origin = metadata.get("coordinate_frame", {}).get("origin_wgs84")
        if not origin:
            raise ValueError("metadata.json has no coordinate_frame.origin_wgs84")
        paths = NATIVE_FILES if selected_file in (None, "metadata.json", "camera_poses.jsonl") else (selected_file,)
        for name in paths:
            path = folder / name
            if path.exists() and name in NATIVE_FILES:
                add_native_tracks(path, "reference" if name == NATIVE_FILES[0] else "sensor", origin, metadata, tracks)
        pose_path = folder / "camera_poses.jsonl"
        if pose_path.exists():
            add_cameras(pose_path, origin, metadata, cameras)
        utc = start_utc(metadata)
        title = metadata.get("instance") or folder.name

    if not tracks and not cameras:
        raise ValueError("No track or camera pose rows found in the selected input")
    for track in tracks.values():
        track["samples"].sort(key=lambda sample: sample[0])
    for camera in cameras.values():
        camera["samples"].sort(key=lambda sample: sample[0])
    times = [sample[0] for group in (*tracks.values(), *cameras.values()) for sample in group["samples"]]
    if utc:
        utc = datetime.fromisoformat(utc.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return {"title": title, "input": selected.name, "start_utc": utc,
            "time_min": min(times), "time_max": max(times), "origin": origin,
            "tracks": list(tracks.values()), "cameras": list(cameras.values())}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Replay track and camera poses on an OpenStreetMap basemap")
    parser.add_argument("--track", type=Path, required=True, metavar="FOLDER_OR_JSONL")
    parser.add_argument("--port", type=int, default=8781)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args(argv)
    try:
        dataset = load_dataset(args.track)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    payload = json.dumps(dataset, separators=(",", ":"), allow_nan=False).encode("utf-8")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            route = urlsplit(self.path).path
            if route == "/api/data":
                body, mime = payload, "application/json; charset=utf-8"
            elif route in ("/", "/index.html", "/app.js", "/style.css"):
                name = "index.html" if route == "/" else route.lstrip("/")
                body = (HERE / name).read_bytes()
                mime = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
                        ".css": "text/css; charset=utf-8"}[Path(name).suffix]
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format_string, *values):
            sys.stderr.write("viewer: " + format_string % values + "\n")

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{server.server_port}/"
    print(f"Track viewer: {url}", flush=True)
    print(f"Loaded {len(dataset['tracks'])} tracks and {len(dataset['cameras'])} cameras from {args.track}", flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
