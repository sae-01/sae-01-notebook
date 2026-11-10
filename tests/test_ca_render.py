import os
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "projects" / "ca"))
import render  # noqa: E402


class PngTests(unittest.TestCase):
    def test_write_png_structure(self):
        w, h = 5, 3
        rows = [bytes([i * 10] * (3 * w)) for i in range(h)]
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "t.png")
            render.write_png(p, w, h, rows)
            data = open(p, "rb").read()
        self.assertTrue(data.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertEqual(data[12:16], b"IHDR")
        self.assertEqual(struct.unpack(">II", data[16:24]), (w, h))
        i = data.index(b"IDAT")
        n = struct.unpack(">I", data[i - 4:i])[0]
        raw = zlib.decompress(data[i + 4:i + 4 + n])
        self.assertEqual(len(raw), h * (1 + 3 * w))
        self.assertEqual(raw[0], 0)


class PaletteTests(unittest.TestCase):
    def test_endpoints_exact(self):
        for name, stops in render.PALETTES.items():
            self.assertEqual(render.palette_color(name, 0.0), stops[0])
            self.assertEqual(render.palette_color(name, 1.0), stops[-1])

    def test_midpoint_mono(self):
        self.assertEqual(render.palette_color("mono", 0.5), (128, 128, 128))


class RenderTests(unittest.TestCase):
    def test_sizes(self):
        for mode in ("age", "trace"):
            w, h, rows = render.render("B3/S23", 20, 12, 10, mode=mode,
                                       scale=3, patch=(10, 6))
            self.assertEqual((w, h), (60, 36))
            self.assertEqual(len(rows), 36)
            self.assertTrue(all(len(r) == 3 * 60 for r in rows))

    def test_deterministic(self):
        for mode in ("age", "trace"):
            a = render.render("B3/S23", 24, 16, 15, mode=mode, seed=5)
            b = render.render("B3/S23", 24, 16, 15, mode=mode, seed=5)
            c = render.render("B3/S23", 24, 16, 15, mode=mode, seed=6)
            self.assertEqual(a, b)
            self.assertNotEqual(a, c)

    def test_bad_args(self):
        with self.assertRaises(ValueError):
            render.render("B3/S23", 8, 8, 1, mode="nope")
        with self.assertRaises(ValueError):
            render.render("B3/S23", 8, 8, 1, palette="nope")


if __name__ == "__main__":
    unittest.main()
