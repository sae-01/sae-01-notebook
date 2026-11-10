import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "projects" / "ca"))
import ca  # noqa: E402
import objects  # noqa: E402

B, S = ca.parse_rule("B3/S23")
GLIDER = [(1, 0), (2, 1), (0, 2), (1, 2), (2, 2)]


def make(w, h, cells):
    g = bytearray(w * h)
    for x, y in cells:
        g[y * w + x] = 1
    return g


class ObjectTests(unittest.TestCase):
    def test_glider(self):
        r = objects.classify(GLIDER, B, S)
        self.assertEqual(r["kind"], "spaceship")
        self.assertEqual(r["period"], 4)
        self.assertEqual((abs(r["dx"]), abs(r["dy"])), (1, 1))

    def test_blinker_block_single(self):
        r = objects.classify([(0, 0), (1, 0), (2, 0)], B, S)
        self.assertEqual((r["kind"], r["period"]), ("oscillator", 2))
        r = objects.classify([(0, 0), (1, 0), (0, 1), (1, 1)], B, S)
        self.assertEqual((r["kind"], r["period"]), ("still", 1))
        self.assertEqual(objects.classify([(5, 5)], B, S)["kind"], "dies")

    def test_block_across_corner(self):
        w = h = 10
        g = make(w, h, [(w - 1, h - 1), (0, h - 1), (w - 1, 0), (0, 0)])
        comps = objects.components(g, w, h)
        self.assertEqual(len(comps), 1)
        self.assertEqual(len(comps[0]), 4)
        self.assertEqual(objects.classify(comps[0], B, S)["kind"], "still")

    def test_canonical_rotation(self):
        rot = [(-y, x) for x, y in GLIDER]
        a = objects.canonical(objects.normalize(GLIDER)[0])
        b = objects.canonical(objects.normalize(rot)[0])
        self.assertEqual(a, b)

    def test_census_smoke(self):
        entries = objects.census("B3/S23", size=48, steps=600, seed=0)
        self.assertTrue(any(e["kind"] in ("still", "oscillator")
                            for e in entries))
        self.assertTrue(all(e["count"] >= 1 for e in entries))



class RadiusTests(unittest.TestCase):
    def test_radius_two_joins_objects_one_cell_apart(self):
        n = 12
        g = bytearray(n * n)
        for x, y in ((2, 2), (3, 2), (2, 3), (3, 3), (5, 2), (6, 2), (5, 3), (6, 3)):
            g[y * n + x] = 1   # two blocks with a one-cell gap
        self.assertEqual(len(objects.components(g, n, n)), 2)
        self.assertEqual(len(objects.components(g, n, n, radius=2)), 1)



class HuntTests(unittest.TestCase):
    def test_glider_next_to_block_still_reported(self):
        # Found 2026-11-10: a glider within 2 cells of debris was grouped
        # with it, and the group's fate hid the glider from the hunt.
        n = 24
        b, s = ca.parse_rule("B3/S23")
        g = bytearray(n * n)
        cells = [(10, 10), (11, 10), (10, 11), (11, 11)]           # block
        cells += [(7, 6), (8, 7), (6, 8), (7, 8), (8, 8)]           # glider heading SE
        for x, y in cells:
            g[y * n + x] = 1
        self.assertEqual(len(objects.components(g, n, n, radius=2)), 1)
        kinds = [r["kind"] for r in objects.classified_objects(g, n, b, s)]
        self.assertIn("spaceship", kinds)


if __name__ == "__main__":
    unittest.main()
