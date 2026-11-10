"""Append a timestamped line to today's journal.

Usage:
  python tools/journal.py "what happened"            # adds "- HH:MM what happened"
  python tools/journal.py --heading "Session 2 — x"   # adds a "## Session 2 — x" heading
  python tools/journal.py --show                      # prints today's journal
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JOURNAL_DIR = ROOT / "memory" / "journal"


def journal_path(day: dt.date, journal_dir: Path = JOURNAL_DIR) -> Path:
    return journal_dir / f"{day.isoformat()}.md"


def _ensure_file(path: Path, day: dt.date) -> None:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {day.isoformat()}\n", encoding="utf-8")


def _append(path: Path, text: str) -> None:
    current = path.read_text(encoding="utf-8")
    sep = "" if current.endswith("\n") else "\n"
    with path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(sep + text + "\n")


def add_entry(text: str, now: dt.datetime | None = None,
              journal_dir: Path = JOURNAL_DIR) -> Path:
    now = now or dt.datetime.now()
    text = text.strip()
    if not text:
        raise ValueError("entry text is empty")
    path = journal_path(now.date(), journal_dir)
    _ensure_file(path, now.date())
    _append(path, f"- {now:%H:%M} {text}")
    return path


def add_heading(title: str, now: dt.datetime | None = None,
                journal_dir: Path = JOURNAL_DIR) -> Path:
    now = now or dt.datetime.now()
    title = title.strip()
    if not title:
        raise ValueError("heading is empty")
    path = journal_path(now.date(), journal_dir)
    _ensure_file(path, now.date())
    _append(path, f"\n## {title}")
    return path


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("text", nargs="*", help="entry text")
    p.add_argument("--heading", help="add a section heading instead of an entry")
    p.add_argument("--show", action="store_true", help="print today's journal")
    args = p.parse_args(argv)

    if args.heading:
        print(f"heading added to {add_heading(args.heading)}")
    if args.text:
        print(f"entry added to {add_entry(' '.join(args.text))}")
    if args.show:
        path = journal_path(dt.date.today())
        print(path.read_text(encoding="utf-8") if path.exists() else "(no journal today)")
    if not (args.heading or args.text or args.show):
        p.print_help()
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
