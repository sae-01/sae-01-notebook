"""Recall benchmark: realistic questions with known answers.

Run when memory grows, to see whether search still finds things:
    python tools/recall_eval.py [-k 3]

A case passes if a chunk from the expected file, containing the expected
phrase, is in the top k results. Kept in a .py file (not markdown) so the
questions don't get indexed and find themselves. Add a case whenever a real
search misses.
"""
from __future__ import annotations

import argparse
import sys

import recall

# (question, expected file, phrase from the answer's chunk). From the
# 2026-11-10 recall test; questions deliberately avoid the source's wording.
CASES = [
    ("which model should do coding work", "AGENTS.md", "sonnet"),
    ("how do I run the tests", "", "unittest discover"),
    ("may I talk to other claude sessions", "memory/notes.md", "feel free"),
    ("why markdown instead of a database", "memory/journal/", "No database"),
    ("console prints weird symbols", "memory/notes.md", "cp1252"),
    ("how long should notes be", "AGENTS.md", "100 lines"),
    ("who built task.py", "", "task.py"),
    ("what python version is installed", "memory/notes.md", "Python 3.10"),
    ("should I create another agent", "", "instance"),
    ("when to summarize the week", "AGENTS.md", "rollups"),
]


def evaluate(k: int = 3, root=recall.ROOT) -> list[tuple[str, bool, str]]:
    """Return (question, passed, top source) for each case."""
    chunks = recall.load_markdown(root) + recall.load_git(root)
    index = recall.BM25(chunks)
    results = []
    for question, source, phrase in CASES:
        hits = index.search(question, k)
        ok = any(c.source.startswith(source) and phrase.lower() in c.text.lower()
                 for _, c in hits)
        top = f"{hits[0][1].source}:{hits[0][1].line}" if hits else "no hits"
        results.append((question, ok, top))
    return results


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Recall benchmark.")
    p.add_argument("-k", type=int, default=3, help="pass if answer is in top k")
    args = p.parse_args(argv)
    results = evaluate(args.k)
    for question, ok, top in results:
        print(f"{'PASS' if ok else 'MISS'}  {question!r}  (top: {top})")
    passed = sum(ok for _, ok, _ in results)
    print(f"\n{passed}/{len(results)} found in top {args.k}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
