import os
import random
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "projects" / "ca"))
import ca  # noqa: E402
import ship  # noqa: E402

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None

GLIDER = "###/#../.#."
PAL4 = [(0, 0, 0), (255, 0, 0), (0, 255, 0), (0, 0, 255)]


class ShapeTests(unittest.TestCase):
    def test_parse_shape(self):
        self.assertEqual(len(ship.parse_shape(GLIDER)), 5)

    def test_glider_moves_diagonally(self):
        b, s = ca.parse_rule("B3/S23")
        start = ship.parse_shape(GLIDER)
        cur = start
        for _ in range(4):
            cur = ship.step(cur, b, s)
        ox, oy = ship._origin(start)
        nx, ny = ship._origin(cur)
        self.assertEqual((abs(nx - ox), abs(ny - oy)), (1, 1))
        self.assertEqual(ship._norm(cur), ship._norm(start))

    def test_strip_and_period(self):
        w, h, rows = ship.strip("B3/S23", GLIDER, scale=4)
        self.assertEqual(len(rows), h)
        self.assertTrue(all(len(r) == 3 * w for r in rows))
        b, s = ca.parse_rule("B3/S23")
        self.assertEqual(ship.find_period(b, s, ship.parse_shape(GLIDER))[0], 4)

    def test_isolated_survival(self):
        self.assertEqual(ship.step({(0, 0)}, frozenset({3}), frozenset({0})), {(0, 0)})

    def test_dying_shape_raises(self):
        with self.assertRaises(ValueError):
            ship.strip("B3/S23", "#")

    def test_flight_frames(self):
        w, h, frames, pal = ship.flight("B3/S23", GLIDER, 8, scale=3)
        self.assertEqual(len(frames), 9)
        self.assertTrue(all(len(f) == w * h for f in frames))
        self.assertTrue(all(max(f) < len(pal) for f in frames))


class GifTests(unittest.TestCase):
    def _write(self, w, h, frames, palette):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        p = os.path.join(d.name, "t.gif")
        ship.write_gif(p, w, h, frames, palette)
        return p

    def _check(self, path, frames, palette):
        back = {tuple(c): i for i, c in enumerate(palette)}
        with Image.open(path) as img:
            self.assertEqual(img.n_frames, len(frames))
            for i, f in enumerate(frames):
                img.seek(i)
                px = img.convert("RGB").getdata()
                self.assertEqual(bytes(back[tuple(c)] for c in px), f)

    def test_markers(self):
        p = self._write(3, 2, [bytes([0, 1, 2, 3, 0, 1]), bytes([3] * 6)], PAL4)
        data = Path(p).read_bytes()
        self.assertTrue(data.startswith(b"GIF89a"))
        self.assertTrue(data.endswith(b";"))

    @unittest.skipUnless(Image, "Pillow not available")
    def test_roundtrip_small(self):
        frames = [bytes([0, 1, 2, 3, 0, 1]), bytes([3, 2, 1, 0, 3, 2])]
        self._check(self._write(3, 2, frames, PAL4), frames, PAL4)

    @unittest.skipUnless(Image, "Pillow not available")
    def test_roundtrip_random(self):
        rnd = random.Random(1234)
        w, h = 97, 61
        frames = [bytes(rnd.randrange(16) for _ in range(w * h)) for _ in range(2)]
        pal = [(i * 16, 255 - i * 16, i * 8) for i in range(16)]
        self._check(self._write(w, h, frames, pal), frames, pal)


if __name__ == "__main__":
    unittest.main()
