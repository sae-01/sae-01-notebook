"""Lint the agent's memory files against the upkeep rules in AGENTS.md."""
import re
import sys
from pathlib import Path

MAX_NOTES_LINES = 100
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
SPAN_RE = re.compile(r"`([^`\n]+)`")
PATH_PREFIXES = ("tools/", "memory/", "docs/", "tests/", "projects/")
PLACEHOLDERS = ("YYYY", "<", ">", "*", "{")


def _read_lines(path: Path):
    return path.read_text(encoding="utf-8").splitlines()


def check_notes_length(root: Path) -> list[str]:
    notes = root / "memory" / "notes.md"
    if not notes.exists():
        return []
    n = len(_read_lines(notes))
    if n > MAX_NOTES_LINES:
        return [f"memory/notes.md:{n}: notes.md has {n} lines (max {MAX_NOTES_LINES})"]
    return []


def check_lesson_dates(root: Path) -> list[str]:
    notes = root / "memory" / "notes.md"
    if not notes.exists():
        return []
    warnings = []
    in_lessons = False
    bullets = []  # (first line number, [lines])
    for i, line in enumerate(_read_lines(notes), 1):
        if line.startswith("## "):
            in_lessons = line.strip() == "## Lessons"
            continue
        if not in_lessons:
            continue
        if line.startswith("- "):
            bullets.append((i, [line]))
        elif bullets and line[:1] in (" ", "\t") and line.strip():
            bullets[-1][1].append(line)
    for num, lines in bullets:
        if not DATE_RE.search("\n".join(lines)):
            warnings.append(f"memory/notes.md:{num}: lesson has no date")
    return warnings


def _is_repo_path(span: str) -> str | None:
    words = span.split()
    if not words:
        return None
    word = words[0]
    if not word.startswith(PATH_PREFIXES):
        return None
    if any(p in word for p in PLACEHOLDERS):
        return None
    return word


def check_paths(root: Path) -> list[str]:
    files = [root / "AGENTS.md", root / "TASKS.md", root / "memory" / "notes.md"]
    docs = root / "docs"
    if docs.is_dir():
        files += sorted(docs.glob("*.md"))
    warnings = []
    for f in files:
        if not f.exists():
            continue
        rel = f.relative_to(root).as_posix()
        in_fence = False
        for i, line in enumerate(_read_lines(f), 1):
            if line.lstrip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            for m in SPAN_RE.finditer(line):
                word = _is_repo_path(m.group(1))
                if word is None:
                    continue
                target = word[:-1] if word.endswith("/") else word
                if not (root / target).exists():
                    warnings.append(f"{rel}:{i}: path `{word}` does not exist")
    return warnings


def run_all(root: Path) -> list[str]:
    return check_notes_length(root) + check_lesson_dates(root) + check_paths(root)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    root = Path(__file__).resolve().parent.parent
    warnings = run_all(root)
    for w in warnings:
        print(w)
    if not warnings:
        print("ok")
    return 1 if warnings else 0


if __name__ == "__main__":
    sys.exit(main())
