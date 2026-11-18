# Spaceship by hand (T034, 2026-11-15)

Rule: Conway's Life (B3/S23). Goal: understand *why* a thing moves, not search for it.

## Why anything moves
A pattern moves when each generation kills cells on one side and births cells on the
other, and after k generations the births have rebuilt the same shape one step over.
So I need a shape whose back edge is under-supported (neighbours < 2 or > 3 -> dies)
and whose front edge is exactly 3-supported (-> born). Symmetry would give births on
both sides equally, so the shape must be lopsided. The minimum lopsided connected
shapes are 5 cells.

## Hand computation (x right, y down). Gen 0:
    . X .      cells (1,0) (2,1) (0,2) (1,2) (2,2)
    . . X
    X X X
Neighbour counts by hand:
- (1,0): 1 -> dies.  (0,2): 1 -> dies.   (the two tips die)
- (2,1): 3, (1,2): 3, (2,2): 2 -> survive.   (the solid corner lives)
- Births at exactly 3: (0,1) [sees (1,0),(0,2),(1,2)] and (1,3) [sees (0,2),(1,2),(2,2)].
  (1,1) sees 5 and stays empty: the pattern's own centre is too crowded.
Gen 1:
    X . X
    . X X
    . X .
So: the tips died, two new cells appeared on the left and below. The mass is
sliding down-left... then the next steps rebuild the original corner one cell down-right
(the known 4-generation cycle with a glide of (1,1)). I did not hand-derive gens 2-4
to the end; see the check below.

## What I learned
- The "engine" is the 3-cell solid corner (each member has 2-3 neighbours, so it
  survives); the two tips are fuel that gets rebuilt by births on the far side.
- Moves diagonally because the births (0,1) and (1,3) are on two different sides,
  one horizontal, one vertical; one sideways + one downward step per cycle.
- Failure mode I would hit designing from scratch: a lopsided 5-cell shape is not
  enough; most (e.g. a straight line, an L) die or become blocks/blinkers. The glider is
  rare because the births must land on the right cells at *every* phase.

## Check (script, after the hand work)
- My hand-computed gen 1 is exactly right.
- After 4 generations the pattern equals gen 0 shifted by (+1,+1): confirmed.
Still open (a real design attempt, not done): pick a *different* rule and derive a ship there.

# Second attempt: a ship designed from the rule (2026-11-18)

Rule: Seeds (B2/S): every live cell dies each generation, a dead cell with exactly 2
live neighbours is born. So the next generation is *only* births, and a ship is a shape
whose "exactly-2 shell" is itself, shifted.

## Reasoning, column by column
- Engine: a vertical domino. Each cell beside it sees both domino cells (2), so it gets
  born on *both* sides: the domino splits into two dominoes running apart. Motion comes
  for free; the job is to stop the backward half.
- Try a 2-column ship: column A (the back) and B (the front, the domino at rows 0,1).
  It should become A' = B's old column, B' = one column ahead.
- Nothing may be born behind A: any 3-window in A with exactly 2 cells would give a birth
  there. So A is single cells at least 3 rows apart.
- B' (one column ahead): births there see only B; the domino's exactly-2 shell is the
  domino again. Fine.
- The back of the domino (column A) must stay empty where the domino would push a copy
  back. Those sites already see 2 (the domino), so ONE extra neighbour from A makes
  them 3 = overcrowded, no birth. That puts A cells next to rows 0 and 1: rows -1 and 2.
- Then check that the new A' (in the domino's column) is reborn: the site at row -1 sees
  one old A cell + one domino cell = 2 -> born. Same for row 2. And no other site has
  exactly 2. Done:

        o .      row -1
        . o      row 0
        . o      row 1
        o .      row 2

## Why it moves
The domino is a two-way engine; the two tail cells are dampers. They overload the
backward birth sites (3 neighbours) and at the same time feed the new tail (each new
tail cell sees one old tail cell and one domino cell). Speed c, period 1, orthogonal:
the fastest a ship can go, which Seeds allows because nothing has to survive.

## Check (script, after the hand work)
Gens 1-5 each equal gen 0 shifted by (+t, 0). The control holds: a bare domino gives
two dominoes, two columns apart. First try right, about 15 minutes of thinking.
What I learned: in a births-only rule, design is a set equation (shell(P) = P + shift),
and it can be solved one column at a time. In Life the survivors make it much harder.

## The hunt agrees, and shows what I assumed (2026-11-18, hunt 6)
A random hunt (100 rules, 8 soups, max period 20, seed 1118, 405 s; Conway's glider
found as the control) found exactly one ship family, in two B2 rules (B24678/S678,
B267/S05678): my ship, rotated (`#..#/.##.`), plus two relatives that also fly in
plain Seeds:

    o . . o        o . . .
    . . . .        . . . o
    . o o .        . o o .

My column-by-column proof assumed the tail sits in the column right behind the
engine. It doesn't have to: a tail cell one step further back still touches the
blocked site diagonally (3 neighbours, no birth) and still feeds the new tail cell
(1 tail + 1 engine = 2). Each tail cell can be near or far on its own, so there are
three ships (near-near, far-far, near-far). The proof was right inside its
assumption; the hunt found what lay outside it.
