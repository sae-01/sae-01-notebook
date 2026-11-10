"""Object detection for life-like CA: find leftover objects and classify them."""
import argparse
import os
import random
import sys
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ca  # noqa: E402

_NEIGHBORS = [(dx, dy) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dx or dy]


def components(grid, w, h, radius=1):
    """Connected components on the torus, as lists of unwrapped (x, y).

    radius=1 is plain 8-connectivity. Use radius=2 to group cells that can
    interact: two cells 2 apart share a neighbor, so a birth there sees both.

    Coordinates are relative to each component's start cell (plus dx/dy
    steps, never mod), so a component crossing the edge keeps its true
    shape. A component that wraps all the way round may exceed w x h.
    """
    seen = bytearray(w * h)
    out = []
    for i in range(w * h):
        if not grid[i] or seen[i]:
            continue
        seen[i] = 1
        start = (i % w, i // w)
        comp = [start]
        queue = deque([start])
        offsets = [(dx, dy) for dx in range(-radius, radius + 1)
                   for dy in range(-radius, radius + 1) if dx or dy]
        while queue:
            x, y = queue.popleft()
            for dx, dy in offsets:
                nx, ny = x + dx, y + dy
                j = (ny % h) * w + (nx % w)  # wrap only for the lookup
                if grid[j] and not seen[j]:
                    seen[j] = 1
                    comp.append((nx, ny))
                    queue.append((nx, ny))
        out.append(comp)
    return out


def normalize(cells):
    """Shift cells so the bbox starts at (0, 0); return (shape, (minx, miny))."""
    cells = list(cells)
    minx = min(x for x, _ in cells)
    miny = min(y for _, y in cells)
    return frozenset((x - minx, y - miny) for x, y in cells), (minx, miny)


def _live_cells(grid, side):
    """(x, y) of all live cells; uses bytearray.find so sparse grids are fast."""
    cells = []
    i = grid.find(1)
    while i != -1:
        cells.append((i % side, i // side))
        i = grid.find(1, i + 1)
    return cells


def classify(cells, births, survivals, max_period=60):
    """Simulate a component alone on an empty torus and classify it."""
    shape0, _ = normalize(cells)
    pop0 = len(shape0)
    bw = max(x for x, _ in shape0) + 1
    bh = max(y for _, y in shape0) + 1
    side = max(bw, bh) + 2 * max_period + 8  # too big to touch itself
    ox, oy = (side - bw) // 2, (side - bh) // 2
    grid = bytearray(side * side)
    for x, y in shape0:
        grid[(y + oy) * side + x + ox] = 1

    def result(kind, period=0, dx=0, dy=0, shape=shape0, first=0, cycle=None):
        return {"kind": kind, "period": period, "dx": dx, "dy": dy,
                "population": pop0, "shape": shape, "first_seen_gen": first,
                "cycle": cycle or [shape]}

    seen = {}  # shape -> (gen, origin)
    history = []  # shapes by generation (to recover the repeating cycle)
    for gen in range(2 * max_period + 12):
        live = _live_cells(grid, side)
        if not live:
            return result("dies")
        shape, org = normalize(live)
        xs = [x for x, _ in live]
        ys = [y for _, y in live]
        if (min(xs) < 2 or min(ys) < 2
                or max(xs) > side - 3 or max(ys) > side - 3):
            return result("other")  # reached the edge; can't trust the run
        if shape in seen:
            t0, o0 = seen[shape]
            dx, dy = org[0] - o0[0], org[1] - o0[1]
            period = gen - t0
            if dx or dy:
                kind = "spaceship"
            else:
                kind = "still" if period == 1 else "oscillator"
            return result(kind, period, dx, dy, shape, t0, history[t0:gen])
        seen[shape] = (gen, org)
        history.append(shape)
        grid = ca.step(grid, side, side, births, survivals)
    return result("other")


_TRANSFORMS = [
    lambda x, y: (x, y), lambda x, y: (-x, y),
    lambda x, y: (x, -y), lambda x, y: (-x, -y),
    lambda x, y: (y, x), lambda x, y: (-y, x),
    lambda x, y: (y, -x), lambda x, y: (-y, -x),
]


def _render(shape):
    w = max(x for x, _ in shape) + 1
    h = max(y for _, y in shape) + 1
    return "/".join("".join("#" if (x, y) in shape else "." for x in range(w))
                    for y in range(h))


def canonical(shape):
    """Rotation/reflection-invariant string: smallest of the 8 renderings."""
    return min(_render(normalize(t(x, y) for x, y in shape)[0])
               for t in _TRANSFORMS)


def split(cells):
    """Split a set of (unwrapped) cells into plain 8-connected pieces."""
    left = set(cells)
    pieces = []
    while left:
        todo = [left.pop()]
        piece = list(todo)
        while todo:
            x, y = todo.pop()
            for dx, dy in _NEIGHBORS:
                n = (x + dx, y + dy)
                if n in left:
                    left.remove(n)
                    piece.append(n)
                    todo.append(n)
        pieces.append(piece)
    return pieces


def classified_objects(grid, size, births, survivals, max_period=60, max_pop=None):
    """Classify radius-2 groups, then look inside groups made of several pieces.

    Radius 2 keeps interacting objects together (needed for loose
    oscillators). But a glider near debris gets grouped with it, and the
    group as a whole may die, settle, or never repeat. So:
    - a group that dies or is unclassifiable is replaced by its pieces;
    - any other multi-piece group is kept, and any piece that is a
      spaceship on its own is reported as well (it shows the rule HAS
      spaceships, even if this one is about to crash).
    """
    def cls(cells):
        # Skip simulating big blobs (max_pop): spaceships are small, and a
        # big blob alone costs most of the hunt's time.
        if max_pop is not None and len(cells) > max_pop:
            shape, _ = normalize(cells)
            return {"kind": "other", "period": 0, "dx": 0, "dy": 0,
                    "population": len(shape), "shape": shape,
                    "first_seen_gen": 0, "cycle": [shape]}
        return classify(cells, births, survivals, max_period)

    out = []
    for comp in components(grid, size, size, radius=2):
        r = cls(comp)
        pieces = split(comp)
        if len(pieces) == 1:
            out.append(r)
            continue
        sub = [cls(pc) for pc in pieces]
        if r["kind"] in ("other", "dies"):
            out.extend(sub)
        else:
            out.append(r)
            out.extend(x for x in sub if x["kind"] == "spaceship")
    return out


def census(rule, size=64, density=0.35, steps=1000, seed=0, max_period=60,
           max_pop=None):
    """Run a soup, classify leftover objects, and group identical ones."""
    births, survivals = ca.parse_rule(rule)
    rng = random.Random(seed)
    grid = ca.soup(size, size, density, rng)
    for _ in range(steps):
        grid = ca.step(grid, size, size, births, survivals)
    groups = {}
    for r in classified_objects(grid, size, births, survivals, max_period,
                                max_pop):
        # Different phases of one object must group together: use the
        # smallest canonical string over the whole repeating cycle.
        canon, shape = min((canonical(s), s) for s in r["cycle"])
        if r["kind"] in ("dies", "other"):
            canon, shape = canonical(r["shape"]), r["shape"]
        adx, ady = sorted((abs(r["dx"]), abs(r["dy"])))
        key = (r["kind"], r["period"], adx, ady, canon)
        if key in groups:
            groups[key]["count"] += 1
        else:
            speed = f"({adx},{ady})/{r['period']}" if r["kind"] == "spaceship" else ""
            groups[key] = {"kind": r["kind"], "period": r["period"],
                           "speed": speed, "count": 1, "canonical": canon,
                           "population": len(shape)}
    return sorted(groups.values(),
                  key=lambda e: (e["kind"] != "spaceship", -e["count"]))


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Detect and classify CA objects.")
    p.add_argument("rule", help="rule string, e.g. B3/S23")
    p.add_argument("--size", type=int, default=64)
    p.add_argument("--steps", type=int, default=1000)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--density", type=float, default=0.35)
    p.add_argument("--max-period", type=int, default=60)
    a = p.parse_args(argv)
    try:
        entries = census(a.rule, a.size, a.density, a.steps, a.seed,
                         a.max_period)
    except ValueError as e:
        p.error(str(e))
    print(f"{len(entries)} distinct objects "
          f"({sum(e['count'] for e in entries)} total)")
    print(f"{'count':>5}  {'kind':<10} {'period':>6}  {'speed':<10} {'pop':>4}")
    for e in entries[:15]:
        print(f"{e['count']:>5}  {e['kind']:<10} {e['period']:>6}  "
              f"{e['speed']:<10} {e['population']:>4}")
        for row in e["canonical"].split("/"):
            print("        " + row)
    return 0


if __name__ == "__main__":
    sys.exit(main())
