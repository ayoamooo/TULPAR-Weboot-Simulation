from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class WorldPhysicsTests(unittest.TestCase):
    def test_tracks_have_distinct_floor_carpet_and_table_friction(self):
        world = (ROOT / "worlds" / "tulpar_demo.wbt").read_text(encoding="utf-8")
        proto = (ROOT / "protos" / "TULPAR.proto").read_text(encoding="utf-8")

        contacts = {}
        for block in re.findall(r"ContactProperties\s*\{([^}]*)\}", world):
            first = re.search(r'material1\s+"([^"]+)"', block)
            second = re.search(r'material2\s+"([^"]+)"', block)
            friction = re.search(r"coulombFriction\s*\[\s*([0-9.]+)\s*\]", block)
            if first and second and friction:
                contacts[frozenset((first.group(1), second.group(1)))] = float(friction.group(1))

        self.assertEqual(contacts[frozenset(("track", "floor"))], 0.85)
        self.assertEqual(contacts[frozenset(("track", "carpet"))], 1.15)
        self.assertEqual(contacts[frozenset(("track", "table"))], 0.95)
        self.assertIn('contactMaterial "floor"', world)
        self.assertIn('contactMaterial "carpet"', world)
        self.assertEqual(proto.count('contactMaterial "track"'), 4)

    def test_carpet_patch_is_a_thin_surface_not_a_raised_block(self):
        world = (ROOT / "worlds" / "tulpar_demo.wbt").read_text(encoding="utf-8")
        match = re.search(
            r'translation -1\.2 1\.35 (?P<height>[0-9.]+).*?name "carpet test patch"(?P<body>.*?)boundingObject Box',
            world,
            re.DOTALL,
        )
        self.assertIsNotNone(match)
        self.assertEqual(float(match.group("height")), 0.001)
        body = match.group("body")
        self.assertIn("size 2.4 1.55 0.002", body)


if __name__ == "__main__":
    unittest.main()
