"""Spaceship visualiser for Life-like cellular automata (stdlib only).

Usage:
    python projects/ca/ship.py RULE SHAPE [--gens 66] [--scale 12]
                               [--out-prefix projects/ca/art/ship]

SHAPE is a canonical string, rows joined by "/", "#" live, "." dead
(e.g. glider "###/#../.#."). Writes <prefix>_strip.png (one panel per phase,
period+1 panels) and <prefix>_flight.gif (animated flight with a fading
trail), and prints the period and displacement.
"""
import argparse
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ca  # noqa: E402
import render  # noqa: E402

BG, GRID, LIVE, GAP = (18, 18, 24), (40, 40, 52), (255, 190, 90), (10, 10, 14)
TRAIL_START, TRAIL_OLD = (200, 110, 60), (30, 26, 30)
GAP_PX = 4


def parse_shape(s):
    return {(x, y) for y, row in enumerate(s.split("/"))
            for x, ch in enumerate(row) if ch == "#"}


def step(cells, births, survivals):
    counts = Counter((x + dx, y + dy) for x, y in cells
                     for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy)
    nxt = {c for c, n in counts.items()
           if n in (survivals if c in cells else births)}
    if 0 in survivals:  # isolated live cells are absent from `counts`
        nxt |= {c for c in cells if c not in counts}
    return nxt


def _origin(cells):
    return min(x for x, _ in cells), min(y for _, y in cells)


def _norm(cells):
    ox, oy = _origin(cells)
    return frozenset((x - ox, y - oy) for x, y in cells)


def find_period(births, survivals, cells, limit=200):
    """Return (period, displacement (dx, dy), phases 0..period)."""
    phases = [set(cells)]
    base = _norm(cells)
    for n in range(1, limit + 1):
        cur = step(phases[-1], births, survivals)
        if not cur:
            break
        phases.append(cur)
        if _norm(cur) == base:
            (x0, y0), (x1, y1) = _origin(cells), _origin(cur)
            return n, (x1 - x0, y1 - y0), phases
    raise ValueError("no repeat found: shape dies or is not a spaceship")


def _bbox(phases):
    pts = [c for p in phases for c in p]
    xs, ys = [x for x, _ in pts], [y for _, y in pts]
    return min(xs), min(ys), max(xs), max(ys)


def strip(rule, shape, scale=12):
    """Panels for phases 0..period side by side -> (width, height, rows)."""
    births, survivals = ca.parse_rule(rule)
    _, _, phases = find_period(births, survivals, parse_shape(shape))
    x0, y0, x1, y1 = _bbox(phases)
    x0, y0, x1, y1 = x0 - 1, y0 - 1, x1 + 1, y1 + 1
    pw = (x1 - x0 + 1) * scale
    n = len(phases)
    width, height = n * pw + (n - 1) * GAP_PX, (y1 - y0 + 1) * scale
    cell_px = {live: bytes(LIVE if live else BG) * (scale - 1) + bytes(GRID)
               for live in (False, True)}
    gap = bytes(GAP) * GAP_PX
    grid_line = gap.join([bytes(GRID) * pw] * n)
    rows = []
    for y in range(y0, y1 + 1):
        line = gap.join(b"".join(cell_px[(x, y) in p] for x in range(x0, x1 + 1))
                        for p in phases)
        rows.extend([line] * (scale - 1) + [grid_line])
    return width, height, rows


def _lerp(a, b, t):
    return tuple(round(u + (v - u) * t) for u, v in zip(a, b))


def flight(rule, shape, gens, scale=6):
    """Animate `gens` generations -> (width, height, frames, palette)."""
    births, survivals = ca.parse_rule(rule)
    cur = parse_shape(shape)
    history = [cur]
    for _ in range(gens):
        cur = step(cur, births, survivals)
        history.append(cur)
    x0, y0, x1, y1 = _bbox([h for h in history if h])
    x0, y0, x1, y1 = x0 - 3, y0 - 3, x1 + 3, y1 + 3
    width, height = (x1 - x0 + 1) * scale, (y1 - y0 + 1) * scale
    # 0 bg, 1 live, 2..12 trail for k=1..11, 13 faint old trail (k >= 12)
    palette = [BG, LIVE] + [_lerp(TRAIL_START, BG, (k - 1) / 12) for k in range(1, 12)]
    palette.append(TRAIL_OLD)
    last, frames = {}, []
    for t, cells in enumerate(history):
        for c in cells:
            last[c] = t
        buf = bytearray(width * height)
        for (x, y), g in last.items():
            block = bytes([min(1 + t - g, 13)]) * scale
            for r in range((y - y0) * scale, (y - y0 + 1) * scale):
                o = r * width + (x - x0) * scale
                buf[o:o + scale] = block
        frames.append(bytes(buf))
    return width, height, frames, palette


def _lzw(data, mcs):
    """GIF variable-width LZW; returns the packed (LSB-first) byte stream."""
    clear, eoi = 1 << mcs, (1 << mcs) + 1
    out, acc, nbits = bytearray(), 0, 0

    def emit(code, width):
        nonlocal acc, nbits
        acc |= code << nbits
        nbits += width
        while nbits >= 8:
            out.append(acc & 255)
            acc >>= 8
            nbits -= 8

    width, nxt, table = mcs + 1, eoi + 1, {}
    emit(clear, width)
    code = data[0]
    for p in data[1:]:
        key = (code, p)
        if key in table:
            code = table[key]
            continue
        emit(code, width)
        table[key] = nxt
        nxt += 1
        if nxt > (1 << width) and width < 12:
            width += 1
        if nxt == 4096:  # table full: clear and restart
            emit(clear, width)
            table, nxt, width = {}, eoi + 1, mcs + 1
        code = p
    emit(code, width)
    emit(eoi, width)
    if nbits:
        out.append(acc & 255)
    return bytes(out)


def write_gif(path, width, height, frames, palette, delay_cs=8):
    """Write a looping animated GIF89a; frames are width*height index bytes."""
    if not 1 <= len(palette) <= 256:
        raise ValueError("palette must have 1..256 entries")
    bits = max(2, (len(palette) - 1).bit_length())
    table = list(palette) + [(0, 0, 0)] * ((1 << bits) - len(palette))
    size = width.to_bytes(2, "little") + height.to_bytes(2, "little")
    out = bytearray(b"GIF89a" + size)
    out += bytes([0x80 | ((bits - 1) << 4) | (bits - 1), 0, 0])
    out += b"".join(bytes(c) for c in table)
    out += b"\x21\xff\x0bNETSCAPE2.0\x03\x01\x00\x00\x00"
    for f in frames:
        if len(f) != width * height:
            raise ValueError("frame size mismatch")
        out += b"\x21\xf9\x04\x00" + delay_cs.to_bytes(2, "little") + b"\x00\x00"
        out += b"\x2c\x00\x00\x00\x00" + size + b"\x00" + bytes([bits])
        z = _lzw(f, bits)
        for i in range(0, len(z), 255):
            blk = z[i:i + 255]
            out += bytes([len(blk)]) + blk
        out += b"\x00"
    out += b";"
    with open(path, "wb") as fh:
        fh.write(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Draw a Life-like spaceship.")
    ap.add_argument("rule")
    ap.add_argument("shape")
    ap.add_argument("--gens", type=int, default=66)
    ap.add_argument("--scale", type=int, default=12)
    ap.add_argument("--flight-scale", type=int, default=6)
    ap.add_argument("--out-prefix", default="projects/ca/art/ship")
    a = ap.parse_args(argv)
    births, survivals = ca.parse_rule(a.rule)
    period, disp, _ = find_period(births, survivals, parse_shape(a.shape))
    os.makedirs(os.path.dirname(a.out_prefix) or ".", exist_ok=True)
    w, h, rows = strip(a.rule, a.shape, a.scale)
    png = a.out_prefix + "_strip.png"
    render.write_png(png, w, h, rows)
    fw, fh, frames, pal = flight(a.rule, a.shape, a.gens, a.flight_scale)
    gif = a.out_prefix + "_flight.gif"
    write_gif(gif, fw, fh, frames, pal)
    print(f"period {period}, displacement {disp} per period")
    print(png)
    print(gif)


if __name__ == "__main__":
    main()
