"""Spaceship hunt: object census over many random Life-like rules.

    python projects/ca/hunt.py N [--seed S] [--size 64] [--steps 600]

Prints one line per spaceship type found: rule, period, speed, population,
count, shape. Conway's B3/S23 runs first as a control (it should find the
glider, given enough soup). Rules that explode are skipped: their soup
fills the grid and leaves no separate objects.
"""
import argparse
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ca  # noqa: E402
import objects  # noqa: E402


MAX_POP = 100  # don't simulate blobs bigger than this alone


def hunt(rules, size, steps, seed):
    for i, rule in enumerate(rules, 1):
        print(f"[{i}/{len(rules)}] {rule}", file=sys.stderr, flush=True)
        if ca.run(rule, size=size, steps=200, seed=seed)["classification"] == "explodes":
            yield rule, None
            continue
        ships = [e for e in objects.census(rule, size=size, steps=steps, seed=seed,
                                       max_pop=MAX_POP)
                 if e["kind"] == "spaceship"]
        yield rule, ships


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("n", type=int)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--size", type=int, default=64)
    p.add_argument("--steps", type=int, default=600)
    args = p.parse_args(argv)

    rng = random.Random(args.seed)
    rules = ["B3/S23"] + [ca.random_rule(rng) for _ in range(args.n)]
    t0, skipped, found = time.time(), 0, 0
    for rule, ships in hunt(rules, args.size, args.steps, args.seed):
        if ships is None:
            skipped += 1
            continue
        for e in ships:
            found += 1
            print(f"{rule}  p{e['period']}  {e['speed']}  pop {e['population']}"
                  f"  x{e['count']}  {e['canonical']}", flush=True)
    print(f"\n{len(rules)} rules, {skipped} exploded (skipped), "
          f"{found} spaceship types, {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
