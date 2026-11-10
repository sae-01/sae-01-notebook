import datetime as dt
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import journal  # noqa: E402

NOW = dt.datetime(2026, 11, 10, 9, 5)


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def read(self):
        return (self.dir / "2026-11-10.md").read_text(encoding="utf-8")

    def test_creates_file_with_title(self):
        journal.add_entry("hello", NOW, self.dir)
        self.assertEqual(self.read(), "# 2026-11-10\n- 09:05 hello\n")

    def test_appends_to_existing_without_trailing_newline(self):
        (self.dir / "2026-11-10.md").write_text("# 2026-11-10\n- old", encoding="utf-8")
        journal.add_entry("new", NOW, self.dir)
        self.assertEqual(self.read(), "# 2026-11-10\n- old\n- 09:05 new\n")

    def test_heading(self):
        journal.add_heading("Session 2", NOW, self.dir)
        journal.add_entry("x", NOW, self.dir)
        self.assertEqual(self.read(), "# 2026-11-10\n\n## Session 2\n- 09:05 x\n")

    def test_unicode_roundtrip(self):
        journal.add_entry("dash — ok", NOW, self.dir)
        self.assertIn("dash — ok", self.read())

    def test_empty_rejected(self):
        with self.assertRaises(ValueError):
            journal.add_entry("   ", NOW, self.dir)
        with self.assertRaises(ValueError):
            journal.add_heading("", NOW, self.dir)


if __name__ == "__main__":
    unittest.main()
