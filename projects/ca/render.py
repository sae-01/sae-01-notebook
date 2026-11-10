"""Render the history of Life-like cellular automata as PNG images (stdlib only).

Modes:
  age   - color = how long a cell has been alive; recently dead cells fade out.
  trace - color = how many generations a cell was alive (heat map).
"""
import argparse
import math
import random
import struct
import sys
import time
import zlib
from itertools import repeat
from operator import mul, add
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ca  # noqa: E402

# Palettes: lists of (r, g, b) stops, evenly spaced over t in [0, 1].
PALETTES = {
    "ember": [(0, 0, 0), (40, 4, 6), (120, 12, 14), (214, 70, 14),
              (250, 160, 40), (255, 236, 170)],
    "ice": [(0, 0, 0), (6, 14, 50), (14, 70, 120), (40, 160, 170),
            (160, 228, 228), (255, 255, 255)],
    "ink": [(250, 246, 236), (200, 196, 188), (130, 128, 126),
            (60, 60, 64), (14, 14, 18)],
    "aurora": [(4, 6, 18), (30, 12, 70), (90, 30, 140), (30, 140, 130),
               (80, 230, 140), (220, 255, 200)],
    "mono": [(0, 0, 0), (255, 255, 255)],
}


def palette_color(name, t):
    """Linearly interpolated RGB (ints) at t in [0, 1]; endpoints are exact."""
    stops = PALETTES[name]
    t = min(1.0, max(0.0, t))
    if t >= 1.0:
        return stops[-1]
    pos = t * (len(stops) - 1)
    i = int(pos)
    f = pos - i
    a, b = stops[i], stops[i + 1]
    return tuple(int(round(a[k] + (b[k] - a[k]) * f)) for k in range(3))


def palette_lut(name, n=256):
    """n colors as 3-byte strings, index 0..n-1 spanning t=0..1."""
    return [bytes(palette_color(name, i / (n - 1))) for i in range(n)]


def write_png(path, width, height, rows):
    """Write 8-bit RGB PNG; rows are `height` bytes objects of 3*width bytes."""
    if len(rows) != height:
        raise ValueError("row count != height")
    raw = bytearray()
    for r in rows:
        if len(r) != 3 * width:
            raise ValueError("bad row length")
        raw.append(0)  # filter type 0
        raw += r

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 6))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


def _make_grid(w, h, density, rng, patch):
    if not patch:
        return ca.soup(w, h, density, rng)
    pw, ph = min(patch[0], w), min(patch[1], h)
    sub = ca.soup(pw, ph, density, rng)
    grid = bytearray(w * h)
    x0, y0 = (w - pw) // 2, (h - ph) // 2
    for y in range(ph):
        o = (y0 + y) * w + x0
        grid[o:o + pw] = sub[y * pw:(y + 1) * pw]
    return grid


_INVERT = bytes([1, 0]) + bytes(254)


def _rows_from_indices(idx, w, h, lut, scale):
    pal = [c * scale for c in lut]
    rows = []
    for y in range(h):
        row = b"".join([pal[i] for i in idx[y * w:(y + 1) * w]])
        rows.extend(repeat(row, scale))
    return rows


def render(rule, w, h, gens, mode="age", palette="ember", seed=0,
           density=0.35, patch=None, scale=4, log=True, fade=48, gamma=1.0):
    """Simulate `gens` generations and return (width, height, rows)."""
    if mode not in ("age", "trace"):
        raise ValueError(f"bad mode: {mode!r}")
    if palette not in PALETTES:
        raise ValueError(f"bad palette: {palette!r}")
    births, survivals = ca.parse_rule(rule)
    rng = random.Random(seed)
    grid = _make_grid(w, h, density, rng, patch)
    n = w * h
    lut = palette_lut(palette)
    one = repeat(1)

    if mode == "trace":
        counts = list(grid)
        for _ in range(gens):
            grid = ca.step(grid, w, h, births, survivals)
            counts = list(map(add, counts, grid))
        top = max(counts) or 1
        if log:
            norm = {c: math.log1p(c) / math.log1p(top) for c in set(counts)}
        else:
            norm = {c: c / top for c in set(counts)}
        table = {c: lut[int(round((v ** gamma) * 255))] for c, v in norm.items()}
        pal = {c: col * scale for c, col in table.items()}
        rows = []
        for y in range(h):
            row = b"".join([pal[c] for c in counts[y * w:(y + 1) * w]])
            rows.extend(repeat(row, scale))
        return w * scale, h * scale, rows

    # age mode
    age = list(grid)
    dead = [0 if g else fade for g in grid]
    for _ in range(gens):
        grid = ca.step(grid, w, h, births, survivals)
        inv = grid.translate(_INVERT)
        age = list(map(mul, map(add, age, one), grid))
        dead = list(map(mul, map(add, dead, repeat(1)), inv))
    cap = max(max(age), 1)
    cap = min(cap, 200)
    lcap = math.log1p(cap)
    # alive: upper half of palette, older = brighter; dead: lower half fading.
    age_lut = {a: 128 + int(round(127 * min(1.0, math.log1p(a) / lcap)))
               for a in set(age) if a}
    dead_lut = {d: int(round(112 * max(0.0, 1.0 - d / fade) ** 1.5))
                for d in set(dead)}
    idx = [age_lut[a] if a else dead_lut[d] for a, d in zip(age, dead)]
    return w * scale, h * scale, _rows_from_indices(idx, w, h, lut, scale)


def main(argv=None):
    p = argparse.ArgumentParser(description="Render CA history as PNG.")
    p.add_argument("rule")
    p.add_argument("--w", type=int, default=320)
    p.add_argument("--h", type=int, default=180)
    p.add_argument("--gens", type=int, default=300)
    p.add_argument("--mode", choices=["age", "trace"], default="age")
    p.add_argument("--palette", choices=sorted(PALETTES), default="ember")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--density", type=float, default=0.35)
    p.add_argument("--patch", type=int, nargs=2, metavar=("W", "H"))
    p.add_argument("--scale", type=int, default=4)
    p.add_argument("--linear", action="store_true",
                   help="trace mode: linear instead of log scaling")
    p.add_argument("--fade", type=int, default=48,
                   help="age mode: generations a dead cell's trail lasts")
    p.add_argument("--gamma", type=float, default=1.0)
    p.add_argument("-o", "--output", default="projects/ca/art/out.png")
    a = p.parse_args(argv)
    t0 = time.time()
    try:
        W, H, rows = render(a.rule, a.w, a.h, a.gens, a.mode, a.palette,
                            a.seed, a.density, tuple(a.patch) if a.patch else None,
                            a.scale, log=not a.linear, fade=a.fade,
                            gamma=a.gamma)
    except ValueError as e:
        p.error(str(e))
    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_png(out, W, H, rows)
    print(f"{out} {W}x{H} {time.time() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
