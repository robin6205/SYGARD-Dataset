"""Checks that the viewer reads released dataset files without changing them."""

import unittest
from pathlib import Path

from app import camera_direction, enu_to_wgs84, load_dataset


ROOT = Path(__file__).resolve().parent.parent


class ViewerDataTests(unittest.TestCase):
    def test_enu_origin_and_camera_direction(self):
        origin = {"latitude_deg": 41.980103, "longitude_deg": -87.903868, "altitude_m": 2250.0}
        latitude, longitude, altitude = enu_to_wgs84([0, 0, 0], origin)
        self.assertAlmostEqual(latitude, origin["latitude_deg"], places=6)
        self.assertAlmostEqual(longitude, origin["longitude_deg"], places=6)
        self.assertAlmostEqual(altitude, origin["altitude_m"], places=1)
        heading, pitch = camera_direction([0.9622989892959595, 0.24528691172599792,
                                           0.11389558017253876, -0.02903161570429802])
        self.assertAlmostEqual(heading, 61.4, delta=.1)
        self.assertAlmostEqual(pitch, 13.5, delta=.1)

    def test_drone_folder_and_aircraft_file(self):
        drone = load_dataset(ROOT / "ord_drone_2026-09-28_1800z_3hz")
        self.assertEqual(len([t for t in drone["tracks"] if t["kind"] == "reference"]), 1)
        self.assertEqual(len(drone["cameras"]), 3)
        self.assertEqual(drone["start_utc"], "2026-09-28T18:00:00Z")
        self.assertEqual({t["label"] for t in drone["tracks"] if t["camera_match"] == "drone01"},
                         {"Camera track 18", "Camera track 23", "Camera track 25"})
        drone_pose = next(t for t in drone["tracks"] if t["kind"] == "reference")["samples"][0]
        self.assertAlmostEqual(drone_pose[5], 267.2, delta=.2)
        aircraft_file = ROOT / "ord_aircraft_2026-09-28_1800z_3hz" / "simulation_poses_native.jsonl"
        aircraft = load_dataset(aircraft_file)
        self.assertEqual(len(aircraft["tracks"]), 39)
        self.assertEqual(len(aircraft["cameras"]), 3)
        aircraft_pose = next(t for t in aircraft["tracks"] if t["kind"] == "reference")["samples"][0]
        self.assertIsInstance(aircraft_pose[5], float)


if __name__ == "__main__":
    unittest.main()
