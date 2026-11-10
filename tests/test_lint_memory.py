import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import lint_memory  # noqa: E402


def make(root: Path, rel: str, text: str):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


class LintMemoryTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def test_length_ok(self):
        make(self.root, "memory/notes.md", "x\n" * 100)
        self.assertEqual(lint_memory.check_notes_length(self.root), [])

    def test_length_too_long(self):
        make(self.root, "memory/notes.md", "x\n" * 101)
        w = lint_memory.check_notes_length(self.root)
        self.assertEqual(len(w), 1)
        self.assertIn("101", w[0])

    def test_lessons_dated_ok(self):
        make(self.root, "memory/notes.md",
             "## Lessons\n- a lesson (2026-11-10)\n- multi\n  line (2026-01-02)\n")
        self.assertEqual(lint_memory.check_lesson_dates(self.root), [])

    def test_lessons_missing_date(self):
        make(self.root, "memory/notes.md",
             "## Facts\n- undated fact\n## Lessons\n- ok (2026-11-10)\n- bad one\n  continued\n## Other\n- nope\n")
        w = lint_memory.check_lesson_dates(self.root)
        self.assertEqual(w, ["memory/notes.md:5: lesson has no date"])

    def test_date_in_continuation_line(self):
        make(self.root, "memory/notes.md",
             "## Lessons\n- first\n  more (2026-03-04)\n")
        self.assertEqual(lint_memory.check_lesson_dates(self.root), [])

    def test_paths_ok(self):
        make(self.root, "tools/wake.py", "")
        (self.root / "memory" / "dir").mkdir(parents=True)
        make(self.root, "AGENTS.md", "Run `tools/wake.py` and see `memory/dir/`.\n")
        self.assertEqual(lint_memory.check_paths(self.root), [])

    def test_paths_missing(self):
        make(self.root, "docs/a.md", "See `tools/nope.py --flag` here.\n")
        w = lint_memory.check_paths(self.root)
        self.assertEqual(len(w), 1)
        self.assertTrue(w[0].startswith("docs/a.md:1:"))
        self.assertIn("tools/nope.py", w[0])

    def test_fenced_code_ignored(self):
        make(self.root, "AGENTS.md", "```\n`tools/nope.py`\n```\nafter\n")
        self.assertEqual(lint_memory.check_paths(self.root), [])

    def test_non_path_first_word_skipped(self):
        make(self.root, "AGENTS.md", 'Run `python tools/recall.py "keywords"`.\n')
        self.assertEqual(lint_memory.check_paths(self.root), [])

    def test_placeholders_skipped(self):
        make(self.root, "TASKS.md",
             "`memory/journal/YYYY-MM-DD.md` `tools/<x>.py` `docs/*.md` `tests/{a}.py`\n")
        self.assertEqual(lint_memory.check_paths(self.root), [])


if __name__ == "__main__":
    unittest.main()
