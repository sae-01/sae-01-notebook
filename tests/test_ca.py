import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "projects" / "ca"))
import ca  # noqa: E402

LIFE = ca.parse_rule("B3/S23")


def make(w, h, cells):
    g = bytearray(w * h)
    for x, y in cells:
        g[y * w + x] = 1
    return g


class RuleTests(unittest.TestCase):
    def test_round_trip(self):
        self.assertEqual(ca.parse_rule("b3/s23"), (frozenset({3}), frozenset({2, 3})))
        self.assertEqual(ca.rule_str(*ca.parse_rule("B63/S32")), "B36/S23")
        self.assertEqual(ca.rule_str(*ca.parse_rule("B/S")), "B/S")
        self.assertEqual(ca.parse_rule("B/S"), (frozenset(), frozenset()))

    def test_junk(self):
        for bad in ["", "junk", "B3", "B9/S1", "3/23", "B3/S2x", "B3S23"]:
            with self.assertRaises(ValueError, msg=bad):
                ca.parse_rule(bad)

    def test_random_rule_never_b0(self):
        rng = random.Random(5)
        for _ in range(200):
            self.assertNotIn(0, ca.parse_rule(ca.random_rule(rng))[0])


class StepTests(unittest.TestCase):
    def test_blinker(self):
        g = make(8, 8, [(3, 4), (4, 4), (5, 4)])
        g1 = ca.step(g, 8, 8, *LIFE)
        self.assertEqual(g1, make(8, 8, [(4, 3), (4, 4), (4, 5)]))
        self.assertEqual(ca.step(g1, 8, 8, *LIFE), g)

    def test_block_still(self):
        g = make(8, 8, [(2, 2), (3, 2), (2, 3), (3, 3)])
        self.assertEqual(ca.step(g, 8, 8, *LIFE), g)

    def test_empty(self):
        g = bytearray(64)
        self.assertEqual(ca.step(g, 8, 8, *LIFE), g)

    def test_glider_returns_after_40(self):
        g = make(10, 10, [(1, 0), (2, 1), (0, 2), (1, 2), (2, 2)])
        cur = g
        for _ in range(40):
            cur = ca.step(cur, 10, 10, *LIFE)
        self.assertEqual(cur, g)


class RunTests(unittest.TestCase):
    def test_dies(self):
        self.assertEqual(ca.run("B/S", size=16, steps=20)["classification"], "dies")

    def test_deterministic(self):
        a = ca.run("B3/S23", size=24, steps=100, seed=7)
        b = ca.run("B3/S23", size=24, steps=100, seed=7)
        self.assertEqual(a, b)

    def test_keys(self):
        r = ca.run("b3/s23", size=16, steps=50)
        self.assertEqual(r["rule"], "B3/S23")
        self.assertEqual(set(r), {"rule", "classification", "period", "settled_at", "final_clustered",
                                  "final_population", "max_population", "steps_run"})



class ClusteredTests(unittest.TestCase):
    def test_dust_ignored_block_counted(self):
        n = 10
        g = bytearray(n * n)
        g[1 * n + 1] = 1                      # lone dot
        for x, y in ((5, 5), (6, 5), (5, 6), (6, 6)):
            g[y * n + x] = 1                  # block
        self.assertEqual(ca.clustered(g, n, n), 4)


if __name__ == "__main__":
    unittest.main()
