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
        name = 'name "carpet test patch"'
        name_index = world.find(name)
        self.assertNotEqual(name_index, -1)
        block_start = world.rfind("Solid {", 0, name_index)
        block_end = world.find("\n}", name_index)
        self.assertNotEqual(block_start, -1)
        self.assertNotEqual(block_end, -1)
        block = world[block_start:block_end + 2]
        body = block[:name_index - block_start]
        after_name = block[name_index - block_start + len(name):]

        height = re.search(r"translation\s+-1\.2\s+1\.35\s+([0-9.]+)", body)
        self.assertIsNotNone(height)
        self.assertEqual(float(height.group(1)), 0.001)
        self.assertRegex(block, r"geometry\s+Box\s*\{\s*size\s+2\.4\s+1\.55\s+0\.002")
        self.assertRegex(after_name, r"boundingObject\s+Box\s*\{\s*size\s+2\.4\s+1\.55\s+0\.002")


if __name__ == "__main__":
    unittest.main()
