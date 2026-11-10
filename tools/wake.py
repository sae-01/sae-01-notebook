"""Orientation on wake: show open tasks, notes, and the latest journal entry.

Usage: python tools/wake.py
"""
from datetime import date, timedelta
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent


def section(title: str, body: str) -> None:
    print(f"\n=== {title} ===")
    print(body.rstrip() or "(empty)")


def open_tasks() -> str:
    path = ROOT / "TASKS.md"
    if not path.exists():
        return "TASKS.md missing"
    lines, keep = [], False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            keep = line.strip() in ("## Now", "## Next")
        if keep:
            lines.append(line)
    return "\n".join(lines)


def latest_journal() -> str:
    files = sorted((ROOT / "memory" / "journal").glob("*.md"))
    if not files:
        return "no journal entries yet"
    return files[-1].read_text(encoding="utf-8")


def recent_commits() -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(ROOT), "log", "--oneline", "-5"],
            capture_output=True, text=True, encoding="utf-8", check=False,
        )
        return out.stdout or out.stderr
    except FileNotFoundError:
        return "git not found"


def missing_rollup(today: date, root: Path = ROOT) -> str | None:
    """Name last ISO week's rollup file if that week had journal days but no rollup."""
    year, week, _ = (today - timedelta(days=7)).isocalendar()
    name = f"{year}-W{week:02d}.md"
    if (root / "memory" / "rollups" / name).exists():
        return None
    for f in (root / "memory" / "journal").glob("*.md"):
        try:
            d = date.fromisoformat(f.stem)
        except ValueError:
            continue
        if d.isocalendar()[:2] == (year, week):
            return name
    return None


if __name__ == "__main__":
    # Windows consoles default to cp1252; force UTF-8 so dashes etc. print cleanly.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    due = missing_rollup(date.today())
    if due:
        section("Reminder", f"Weekly rollup missing: write memory/rollups/{due} (see AGENTS.md).")
    section("Tasks", open_tasks())
    section("Notes", (ROOT / "memory" / "notes.md").read_text(encoding="utf-8"))
    section("Latest journal", latest_journal())
    section("Recent commits", recent_commits())
