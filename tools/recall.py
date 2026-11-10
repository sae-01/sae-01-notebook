"""Search my memory (journal, notes, tasks, docs, git log) with BM25 ranking.

Usage:
  python tools/recall.py "query words"
  python tools/recall.py -n 10 --no-git "query"
Design: docs/recall.md
"""
from __future__ import annotations

import argparse
import math
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_GLOBS = ["memory/**/*.md", "TASKS.md", "AGENTS.md", "docs/**/*.md"]

STOPWORDS = set("""
a an and are as at be but by for from has have i if in into is it its me my no
not of on or so that the their then there these this to was were will with
""".split())

TOKEN_RE = re.compile(r"[a-z0-9]+")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
BULLET_RE = re.compile(r"^(\s*)([-*]|\d+\.)\s+")


@dataclass
class Chunk:
    source: str          # relative path, or "git:<hash>"
    line: int            # 1-based line where the chunk starts
    heading: str         # nearest heading above the chunk ("" if none)
    text: str
    tokens: list[str] = field(default_factory=list)


def stem(word: str) -> str:
    """Very light suffix stripping so 'tests'/'testing'/'tested' meet."""
    for suf in ("ing", "ed", "ly", "es", "s"):
        if len(word) > len(suf) + 2 and word.endswith(suf):
            if suf == "s" and word.endswith("ss"):
                break  # class, process
            word = word[: -len(suf)]
            break
    # Drop a final 'e' so line/lines, note/notes/noted all meet.
    if len(word) > 3 and word.endswith("e"):
        word = word[:-1]
    return word


def tokenize(text: str) -> list[str]:
    return [stem(t) for t in TOKEN_RE.findall(text.lower()) if t not in STOPWORDS]


def chunk_markdown(text: str, source: str) -> list[Chunk]:
    """Split markdown into bullet items / paragraphs, each tagged with its heading."""
    chunks: list[Chunk] = []
    heading = ""
    buf: list[str] = []
    start = 0

    def flush():
        nonlocal buf
        body = "\n".join(buf).strip()
        if body:
            chunks.append(Chunk(source, start, heading, body))
        buf = []

    in_fence = False
    for i, line in enumerate(text.splitlines(), 1):
        # Skip fenced code blocks: examples there are noise, not memories.
        if line.lstrip().startswith("```"):
            flush()
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        h = HEADING_RE.match(line)
        if h:
            flush()
            heading = h.group(2).strip()
            continue
        if not line.strip():
            flush()
            continue
        bullet = BULLET_RE.match(line)
        # A top-level bullet starts a new chunk; indented lines continue the current one.
        if bullet and not bullet.group(1):
            flush()
        if not buf:
            start = i
        buf.append(line)
    flush()
    return chunks


def load_markdown(root: Path) -> list[Chunk]:
    seen: set[Path] = set()
    chunks: list[Chunk] = []
    for pattern in SOURCE_GLOBS:
        for path in sorted(root.glob(pattern)):
            if path in seen or not path.is_file():
                continue
            seen.add(path)
            rel = path.relative_to(root).as_posix()
            chunks.extend(chunk_markdown(path.read_text(encoding="utf-8"), rel))
    return chunks


def load_git(root: Path) -> list[Chunk]:
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "log", "--format=%h%x1f%ad%x1f%B%x1e",
             "--date=short"],
            capture_output=True, text=True, encoding="utf-8", check=False,
        ).stdout
    except FileNotFoundError:
        return []
    chunks = []
    for rec in out.split("\x1e"):
        parts = rec.strip().split("\x1f")
        if len(parts) != 3:
            continue
        h, date, body = parts
        body = "\n".join(l for l in body.splitlines()
                         if not l.startswith("Co-Authored-By:")).strip()
        chunks.append(Chunk(f"git:{h}", 0, date, body))
    return chunks


class BM25:
    def __init__(self, chunks: list[Chunk], k1: float = 1.2, b: float = 0.75):
        self.chunks, self.k1, self.b = chunks, k1, b
        for c in chunks:
            c.tokens = tokenize(c.heading + " " + c.text)
        self.n = len(chunks)
        self.avgdl = (sum(len(c.tokens) for c in chunks) / self.n) if self.n else 0.0
        self.df: Counter[str] = Counter()
        for c in chunks:
            self.df.update(set(c.tokens))
        self.tf = [Counter(c.tokens) for c in chunks]

    def idf(self, term: str) -> float:
        df = self.df.get(term, 0)
        return math.log(1 + (self.n - df + 0.5) / (df + 0.5))

    def search(self, query: str, limit: int = 5) -> list[tuple[float, Chunk]]:
        terms = tokenize(query)
        scored = []
        for c, tf in zip(self.chunks, self.tf):
            dl = len(c.tokens) or 1
            score = 0.0
            for t in terms:
                f = tf.get(t, 0)
                if f:
                    score += self.idf(t) * f * (self.k1 + 1) / (
                        f + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
            if score > 0:
                scored.append((score, c))
        scored.sort(key=lambda sc: -sc[0])
        return scored[:limit]


def format_hit(score: float, c: Chunk) -> str:
    loc = c.source if c.source.startswith("git:") else f"{c.source}:{c.line}"
    head = f"  [{c.heading}]" if c.heading else ""
    body = "\n".join("    " + l for l in c.text.splitlines())
    return f"{score:5.2f}  {loc}{head}\n{body}"


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Search my memory.")
    p.add_argument("query", nargs="+")
    p.add_argument("-n", type=int, default=5, help="number of results")
    p.add_argument("--no-git", action="store_true", help="skip git commit messages")
    args = p.parse_args(argv)

    chunks = load_markdown(ROOT)
    if not args.no_git:
        chunks += load_git(ROOT)
    hits = BM25(chunks).search(" ".join(args.query), args.n)
    if not hits:
        print("no matches")
        return 1
    print("\n\n".join(format_hit(s, c) for s, c in hits))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
