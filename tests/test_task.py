import datetime as dt
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import task  # noqa: E402

SAMPLE = """# Tasks

Format: `- [ ] T### short title — detail`. Keep "Now" to 1–3 items.

## Now
- [ ] T009 Use recall — for real

## Next
- [ ] T006 Research memory
- [ ] T008 Add a tool

## Done
- [x] T007 2026-11-10 Chose project
- [x] T004 2026-11-10 journal
"""
DAY = dt.date(2026, 12, 1)


class TaskTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "TASKS.md"
        self.path.write_bytes(SAMPLE.encode("utf-8"))

    def tearDown(self):
        self.tmp.cleanup()

    def text(self):
        return self.path.read_bytes().decode("utf-8")

    def test_next_id_is_max_plus_one_including_done(self):
        self.assertEqual(task.next_id(SAMPLE.split("\n")), "T010")

    def test_add_to_next(self):
        self.assertEqual(task.add_task("new thing", path=self.path), "T010")
        self.assertEqual(
            self.text(),
            SAMPLE.replace("T008 Add a tool\n", "T008 Add a tool\n- [ ] T010 new thing\n"))

    def test_add_to_now(self):
        task.add_task("urgent — yes", now=True, path=self.path)
        self.assertIn("- [ ] T009 Use recall — for real\n- [ ] T010 urgent — yes\n\n## Next",
                      self.text())

    def test_ids_not_reused(self):
        task.add_task("a", path=self.path)
        task.done_task("T010", DAY, self.path)
        self.assertEqual(task.add_task("b", path=self.path), "T011")

    def test_move_next_to_now(self):
        task.move_task("T006", "Now", self.path)
        t = self.text()
        self.assertIn("T009 Use recall — for real\n- [ ] T006 Research memory\n\n## Next", t)
        self.assertEqual(t.count("T006"), 1)

    def test_move_now_to_next_end(self):
        task.move_task("T009", "Next", self.path)
        self.assertIn("T008 Add a tool\n- [ ] T009 Use recall — for real\n\n## Done", self.text())
        self.assertIn("## Now\n\n## Next", self.text())

    def test_done(self):
        task.done_task("T006", DAY, self.path)
        t = self.text()
        self.assertNotIn("- [ ] T006", t)
        self.assertIn("## Done\n- [x] T006 2026-12-01 Research memory\n- [x] T007", t)

    def test_unknown_id_leaves_file_identical(self):
        before = self.path.read_bytes()
        for fn in (lambda: task.done_task("T999", DAY, self.path),
                   lambda: task.move_task("T999", "Now", self.path)):
            with self.assertRaises(task.TaskError):
                fn()
        self.assertEqual(self.path.read_bytes(), before)

    def test_already_done_error(self):
        before = self.path.read_bytes()
        with self.assertRaises(task.TaskError):
            task.done_task("T007", DAY, self.path)
        with self.assertRaises(task.TaskError):
            task.move_task("T007", "Now", self.path)
        self.assertEqual(self.path.read_bytes(), before)

    def test_empty_text_and_missing_section(self):
        before = self.path.read_bytes()
        with self.assertRaises(task.TaskError):
            task.add_task("   ", path=self.path)
        self.path.write_bytes(b"# Tasks\n\n## Now\n- [ ] T001 x\n")
        before = self.path.read_bytes()
        with self.assertRaises(task.TaskError):
            task.add_task("y", path=self.path)
        with self.assertRaises(task.TaskError):
            task.done_task("T001", DAY, self.path)
        self.assertEqual(self.path.read_bytes(), before)

    def test_other_lines_preserved(self):
        task.add_task("z", path=self.path)
        task.move_task("T006", "Now", self.path)
        task.done_task("T008", DAY, self.path)
        t = self.text()
        for line in SAMPLE.split("\n")[:4] + ["- [x] T007 2026-11-10 Chose project",
                                               "- [x] T004 2026-11-10 journal"]:
            self.assertIn(line, t.split("\n"))
        self.assertTrue(t.endswith("\n"))
        self.assertNotIn("\r", t)

    def test_list(self):
        out = task.list_tasks(self.path)
        self.assertIn("## Now\n- [ ] T009", out)
        self.assertIn("T008", out)
        self.assertNotIn("T007", out)


if __name__ == "__main__":
    unittest.main()
