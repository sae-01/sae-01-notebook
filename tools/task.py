"""Manage TASKS.md (sections Now / Next / Done).

Usage:
  python tools/task.py list                   # print Now and Next
  python tools/task.py add "text" [--now]     # new open item at end of Next (or Now)
  python tools/task.py now T###               # move an open item to end of Now
  python tools/task.py next T###              # move an open item to end of Next
  python tools/task.py done T###              # mark done, insert at top of Done
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS_FILE = ROOT / "TASKS.md"

OPEN_RE = re.compile(r"^- \[ \] (T\d+)(?: (.*))?$")
DONE_RE = re.compile(r"^- \[x\] (T\d+)\b")
ID_RE = re.compile(r"\bT(\d+)\b")


class TaskError(Exception):
    """User-facing error; the file is left unchanged."""


def _load(path: Path) -> list[str]:
    return path.read_bytes().decode("utf-8").split("\n")


def _save(path: Path, lines: list[str]) -> None:
    path.write_bytes("\n".join(lines).encode("utf-8"))


def _section(lines: list[str], name: str) -> tuple[int, int]:
    """Return (header_index, end_index) where end is exclusive."""
    header = f"## {name}"
    start = next((i for i, l in enumerate(lines) if l.rstrip() == header), None)
    if start is None:
        raise TaskError(f"missing section: {header}")
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break
    return start, end


def _append_pos(lines: list[str], name: str) -> int:
    """Index to insert at so the item lands after the section's last content line."""
    start, end = _section(lines, name)
    pos = end
    while pos > start + 1 and not lines[pos - 1].strip():
        pos -= 1
    return pos


def next_id(lines: list[str]) -> str:
    nums = [int(m) for l in lines for m in ID_RE.findall(l)]
    return f"T{max(nums, default=0) + 1:03d}"


def _find_open(lines: list[str], tid: str) -> tuple[int, str]:
    tid = tid.upper()
    for i, l in enumerate(lines):
        m = OPEN_RE.match(l)
        if m and m.group(1) == tid:
            return i, (m.group(2) or "")
    for l in lines:
        m = DONE_RE.match(l)
        if m and m.group(1) == tid:
            raise TaskError(f"{tid} is already done")
    raise TaskError(f"unknown task ID: {tid}")


def add_task(text: str, now: bool = False, path: Path = TASKS_FILE) -> str:
    text = text.strip()
    if not text:
        raise TaskError("task text is empty")
    lines = _load(path)
    pos = _append_pos(lines, "Now" if now else "Next")
    tid = next_id(lines)
    lines.insert(pos, f"- [ ] {tid} {text}")
    _save(path, lines)
    return tid


def move_task(tid: str, section: str, path: Path = TASKS_FILE) -> None:
    lines = _load(path)
    _section(lines, section)  # validate before touching anything
    idx, _ = _find_open(lines, tid)
    item = lines.pop(idx)
    lines.insert(_append_pos(lines, section), item)
    _save(path, lines)


def done_task(tid: str, day: dt.date | None = None, path: Path = TASKS_FILE) -> None:
    day = day or dt.date.today()
    lines = _load(path)
    start, _ = _section(lines, "Done")
    idx, text = _find_open(lines, tid)
    lines.pop(idx)
    start, _ = _section(lines, "Done")  # recompute after removal
    entry = f"- [x] {tid.upper()} {day.isoformat()}" + (f" {text}" if text else "")
    lines.insert(start + 1, entry)
    _save(path, lines)


def list_tasks(path: Path = TASKS_FILE) -> str:
    lines = _load(path)
    out = []
    for name in ("Now", "Next"):
        start, end = _section(lines, name)
        out.append(f"## {name}")
        out.extend(l for l in lines[start + 1:end] if l.strip())
        out.append("")
    return "\n".join(out).rstrip("\n")


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="print Now and Next")
    a = sub.add_parser("add", help="add a task")
    a.add_argument("text", nargs="+")
    a.add_argument("--now", action="store_true", help="add to Now instead of Next")
    for name in ("now", "next", "done"):
        s = sub.add_parser(name)
        s.add_argument("id")
    args = p.parse_args(argv)

    try:
        if args.cmd == "list":
            print(list_tasks())
        elif args.cmd == "add":
            print(add_task(" ".join(args.text), now=args.now))
        elif args.cmd == "now":
            move_task(args.id, "Now")
            print(f"{args.id.upper()} -> Now")
        elif args.cmd == "next":
            move_task(args.id, "Next")
            print(f"{args.id.upper()} -> Next")
        elif args.cmd == "done":
            done_task(args.id)
            print(f"{args.id.upper()} done")
    except (TaskError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
