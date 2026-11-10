"""Small life-like cellular automata engine (Moore neighborhood, torus)."""
import argparse
import json
import random
import re
import sys
from collections import Counter
from operator import add

_RULE_RE = re.compile(r"^B([0-8]*)/S([0-8]*)$")

# Maps cell value 0/1 to 0/10 (used to build lookup-table keys).
_TEN = bytes([0, 10]) + bytes(254)


def parse_rule(s):
    """Parse 'B3/S23' (case-insensitive) into (births, survivals)."""
    if not isinstance(s, str):
        raise ValueError(f"bad rule: {s!r}")
    m = _RULE_RE.match(s.strip().upper())
    if not m:
        raise ValueError(f"bad rule: {s!r}")
    return frozenset(map(int, m.group(1))), frozenset(map(int, m.group(2)))


def rule_str(births, survivals):
    """Canonical rule string with sorted digits, e.g. 'B36/S23'."""
    return "B%s/S%s" % ("".join(map(str, sorted(births))),
                        "".join(map(str, sorted(survivals))))


def random_rule(rng):
    """Random rule; each of B1..B8, S0..S8 is on with p=0.5. B0 is always off."""
    births = {n for n in range(1, 9) if rng.random() < 0.5}
    survivals = {n for n in range(9) if rng.random() < 0.5}
    return rule_str(births, survivals)


def step(grid, w, h, births, survivals):
    """One generation on a w x h torus. grid is row-major, 1 = alive."""
    # table[key]: key = (3x3 sum including the cell itself) + 10 * alive.
    # Neighbor count = sum - alive, hence the (total - 1) for live cells.
    table = bytearray(20)
    for total in range(10):
        table[total] = 1 if total in births else 0
        table[total + 10] = 1 if (total - 1) in survivals else 0
    rows = [bytes(grid[y * w:(y + 1) * w]) for y in range(h)]
    # Horizontal 3-wide sums per row; everything runs in C-level map/add.
    hsum = []
    for r in rows:
        left = r[-1:] + r[:-1]
        right = r[1:] + r[:1]
        hsum.append(list(map(add, map(add, left, r), right)))
    out = bytearray()
    for y in range(h):
        tot = map(add, map(add, hsum[y - 1], hsum[y]), hsum[(y + 1) % h])
        keys = map(add, tot, rows[y].translate(_TEN))
        out += bytes(map(table.__getitem__, keys))
    return out


def soup(w, h, density, rng):
    """Random fill; each cell alive with probability `density`."""
    return bytearray(1 if rng.random() < density else 0 for _ in range(w * h))


_NO_BIRTH = frozenset()
_ANY_NEIGHBOR = frozenset(range(1, 9))


def clustered(grid, w, h):
    """Live cells with at least one live neighbor (ignores isolated 'dust').

    One step of rule B/S12345678 keeps exactly those cells.
    """
    return sum(step(grid, w, h, _NO_BIRTH, _ANY_NEIGHBOR))


def run(rule, size=64, density=0.35, steps=500, seed=0):
    """Simulate from a seeded soup and classify the long-term behaviour."""
    births, survivals = parse_rule(rule)
    rng = random.Random(seed)
    w = h = size
    cells = w * h
    grid = soup(w, h, density, rng)
    seen = {hash(bytes(grid)): 0}  # state hash -> generation first seen
    pop = sum(grid)
    max_pop = pop
    classification, period, settled_at = None, None, None
    gen = 0
    if pop == 0:
        classification, settled_at = "dies", 0
    while classification is None and gen < steps:
        grid = step(grid, w, h, births, survivals)
        gen += 1
        pop = sum(grid)
        max_pop = max(max_pop, pop)
        if pop == 0:
            classification, settled_at = "dies", gen
            break
        key = hash(bytes(grid))
        if key in seen:
            settled_at = seen[key]
            period = gen - settled_at
            classification = "fixed" if period == 1 else "periodic"
            break
        seen[key] = gen
    if classification is None:
        classification = "explodes" if pop / cells > 0.5 else "chaotic"
    return {
        "rule": rule_str(births, survivals),
        "classification": classification,
        "period": period,
        "settled_at": settled_at,
        "final_population": pop,
        "final_clustered": clustered(grid, w, h),
        "max_population": max_pop,
        "steps_run": gen,
    }


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Life-like cellular automata.")
    p.add_argument("rule", nargs="?", help="rule string, e.g. B3/S23")
    p.add_argument("--size", type=int, default=64)
    p.add_argument("--steps", type=int, default=500)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--density", type=float, default=0.35)
    p.add_argument("--survey", type=int, metavar="N",
                   help="sample N random rules and summarize")
    args = p.parse_args(argv)

    if args.survey is not None:
        rng = random.Random(args.seed)
        counts = Counter()
        for _ in range(args.survey):
            r = run(random_rule(rng), args.size, args.density,
                    args.steps, args.seed)
            counts[r["classification"]] += 1
            print(r["rule"], r["classification"], r["period"],
                  r["settled_at"], r["final_population"],
                  r["final_clustered"])
        print()
        for name, n in sorted(counts.items()):
            print(f"{name}: {n}")
        return 0
    if not args.rule:
        p.error("give a rule or --survey N")
    try:
        result = run(args.rule, args.size, args.density, args.steps, args.seed)
    except ValueError as e:
        p.error(str(e))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
