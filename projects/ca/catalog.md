# CA catalog — what I've found

Life-like rules (no B0), 64x64 torus, soup density 0.35, up to 500 steps.
Reproduce a survey: `python projects/ca/ca.py --survey N --seed S`.

## Survey 1 (2026-11-10): 200 random rules, seed 7, 35 s

| class | count |
|---|---|
| explodes | 75 |
| chaotic | 66 |
| fixed | 29 |
| periodic | 28 |
| dies | 2 |

Control: Conway's B3/S23 at seed 0 settles at generation 320 into period 2.

### Leads worth a closer look
- **B346/S047**: long transient (settles at gen 269) into period 4 with only
  47 live cells. Sparse and slow, which is the Life-like signature. First to examine.
- **B3678/S014568**: still chaotic at 500 steps with a low population (311).
  Could be slow-burning structure, or just noise.
- **B457/S012378**: period 24 after a 187-generation transient, pop 596.

### Probably artifacts, not finds
- Long periods (B1678/S23457 p180, B23/S34578 p140, B1/S01378 p60) come with
  dense populations or B1. Likely whole-grid patterns cycling around the
  64-cell torus. Check by changing `--size`: a real oscillator keeps its
  period, a torus artifact's period changes with the grid.

### Size test (2026-11-10, seed 0, sizes 48/64/80)
- B1678/S23457: p180 / no repeat / p420. The period follows the grid, so it's a
  **torus artifact**. Confirmed.
- B346/S047: settles at gen 287 / 287 / 211 into p4 (35 cells) / still
  (39) / p4 (110). The long transient and small p4 debris hold at every size,
  so this is **robust behavior** and my best lead.

### B346/S047 up close (2026-11-10, T020)
Debris at size 80, seed 0, gen 400 (connected components, wrap-spanning skipped):
89 single cells, 2 L-trominoes, plus a few 2-5 cell bits. Each tested alone:
- single cell: still life. **S0 makes a lone cell immortal.**
- L-tromino: becomes a single cell in one step.
- X pentomino (`#.#/.#./#.#`): period 2.
No p4 object among them; the p4 seen earlier comes from something rarer.
**Lesson: S0 rules fake the sparse, Life-like signature.** Low final
population plus a long transient mostly means immortal dust. Future surveys
should count population excluding isolated cells, or skip S0 (T021).

## Survey 2 (2026-11-10): 400 rules, seed 11, dust-free count

New column `final_clustered`: live cells with at least one live neighbor
(so S0 dust doesn't count). 142 chaotic, 133 explode, 75 periodic, 44 fixed, 6 die.

Leads, size-tested at 48 and 80 with seeds 0 and 1, 1500 steps:

| rule | settles at | ends as | non-dust cells |
|---|---|---|---|
| **B4567/S01236** | 338-653 | p8 or p24 | 148-392 |
| **B456/S023568** | 307-745 | still or p2 | 7-40 |
| B35678/S12 | 125-191 | still | 39-131 |
| B456/S02456 | 116-292 | still or p2 | 6-69 |

- **B4567/S01236** is my best lead. Its transient beats Conway's (320 at size
  64) and grows with grid size, as Life's does. Period 24 likely = p8 and p3
  objects together. Object census pending (T019).
- **B456/S023568** has long-lived chaos burning down to a few tiny objects,
  like a Life methuselah but over a whole soup.

## Object census (2026-11-10, `projects/ca/objects.py`)

Control: Conway at size 96, seed 1, 1500 steps finds the glider, blocks,
blinkers, beehives, loaves, boats and ponds: Life's known common objects.

Group objects with **radius 2**, not plain touching: in a Life-like rule, a
dead cell between two objects one cell apart counts neighbors from both, so
they interact. With radius 1, B4567/S01236's p8 vanished from the census.

**B4567/S01236** (size 80, 1500 steps):
- seed 0: 164 still lifes, oscillators p2 x4, p4 x3, p8 x1.
- seed 1: same plus a p6. lcm(2,4,6,8) = 24 = the whole-grid period seen
  in survey 2. Puzzle solved.
- Oscillators are loose: e.g. a 21-cell p4 made of scattered cells that
  hold each other up at distance. No spaceships.

**B456/S023568** (seed 1): 23 still lifes and 3 p2 oscillators. The long
transient burns down to very little.

## Spaceship hunt (2026-11-10, `projects/ca/hunt.py`, T022)

- Run 1: 301 rules, 0 spaceships, including the Conway control. That was a bug
  (glider hidden in a radius-2 group), now fixed with a regression test.
- Run 2: 200 rules at size 96, 1500 steps, timeboxed by the user at 20 min.
  Only the control glider was found. It printed no progress, so it's unknown how
  many rules it covered: **not evidence that spaceships are rare.**
- Speed: ~14 s per rule. Main cost: each small piece is simulated on a
  torus sized for max_period=60 (~136x136). Next run: max_period ~20,
  progress output (added), skip blobs over 100 cells (added).

### What v1 can't tell apart
Exact-repeat detection misses anything that moves: a glider never repeats on
an unbounded grid and only repeats after a full lap on the torus. So
"chaotic" mixes real chaos with moving structures. Next: detect moving
objects (T019).

## Spaceship hunt (T022, 2026-11-10)

`python projects/ca/hunt.py 300 --seed 0 --max-period 20 --soups 6`: 301 rules
(incl. the B3/S23 control), 104 exploded and were skipped, 998 s. Raw output:
`projects/ca/hunt-300.txt`. Speed is (dx,dy)/period.

| Rule | Period | Speed | Pop | Seen | Shape | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| B3/S23 | 4 | c/4 diagonal | 5 | 1 | `###/#../.#.` | control: the glider |
| B3/S235 | 4 | c/4 diagonal | 5 | 1 | `###/#../.#.` | glider survives S5 |
| B256/S357 | 1 | c orthogonal | 4 | 1 | `#..#/.##.` | same c ship in all three B2 rules |
| B248/S0578 | 1 | c orthogonal | 4 | 3 | `#..#/.##.` | |
| B256/S8 | 1 | c orthogonal | 4 | 1 | `#..#/.##.` | |
| B348/S127 | 10 | c/10 orthogonal | 8 | 7 | `####/###./.#..` | slow and common: best lead |
| B3678/S0125 | 10 | c/5 orthogonal | 9 | 1 | `##.../##..#/.#.##/..#..` | |

Method lesson: one 64x64 soup per rule is too small a sample. With 1 soup the
Conway control found the glider at only 1 of 4 seeds; with 6 soups, at 3 of 3.
Ships with period > 20 can't be seen at this cap.

### B348/S127 c/10 ship, close look (T028, 2026-11-10)

Verified alone: returns to its shape shifted 1 cell after 10 generations.
Population cycles 8,6,7,6,9,6,8,6,6,5; it never exceeds a 5x4 box. Phase 0:

```
####
###.
.#..
```

Seen 7 times across 6 soups, so it arises naturally, not by luck. Whether it
is already known (e.g. on Catagolue) is unchecked. Phase dump: run
`objects.classify` on the shape, or load it in the web playground.
