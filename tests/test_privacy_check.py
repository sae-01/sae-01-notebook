import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import privacy_check as pc  # noqa: E402


def kinds(text, terms=()):
    return [(k, m) for _, k, m in pc.scan_text(text, list(terms))]


class PatternTests(unittest.TestCase):
    def test_email(self):
        self.assertIn(("email", "bob@example.com"), kinds("mail bob@example.com now"))  # privacy:ok

    def test_windows_paths(self):
        self.assertEqual(kinds(r"see C:\Work\x.txt")[0][0], "winpath")  # privacy:ok
        self.assertEqual(kinds("see d:/work/x")[0][0], "winpath")  # privacy:ok

    def test_home_paths(self):
        self.assertEqual(kinds("at /Users/bob/x")[0], ("homepath", "/Users/bob"))  # privacy:ok
        self.assertEqual(kinds("at /home/bob/x")[0], ("homepath", "/home/bob"))  # privacy:ok

    def test_ip_hits(self):
        self.assertEqual(kinds("host 192.168.1.20 up"), [("ip", "192.168.1.20")])  # privacy:ok
        self.assertEqual(kinds("at 10.0.0.1."), [("ip", "10.0.0.1")])  # privacy:ok

    def test_versions_not_ip(self):
        for s in ("python 3.10.9", "git 2.45.1", "v1.2.3.4.5", "300.1.1.1"):
            self.assertEqual(kinds(s), [], s)

    def test_secrets(self):
        samples = [
            "sk-" + "a" * 24,
            "ghp_" + "b" * 30,
            "gho_" + "c" * 30,
            "github_pat_" + "d" * 30,
            "AKIA" + "E" * 16,
            "password = hunter2",  # privacy:ok
            "api_key: abc123",  # privacy:ok
            "token=xyz",  # privacy:ok
        ]
        for s in samples:
            self.assertTrue(any(k == "secret" for k, _ in kinds(s)), s)


class TermTests(unittest.TestCase):
    def test_case_insensitive(self):
        self.assertEqual(kinds("Hi JANE Example!", ["jane example"]), [("term", "JANE Example")])

    def test_whole_word(self):
        self.assertEqual(kinds("the annual review", ["ann"]), [])
        self.assertEqual(kinds("ask Ann today", ["ann"]), [("term", "Ann")])

    def test_load_terms(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "privacy.txt"
            p.write_text("# c\n\nFoo\n  bar baz \n", encoding="utf-8")
            self.assertEqual(pc.load_terms(p), ["Foo", "bar baz"])
            self.assertEqual(pc.load_terms(Path(d) / "missing.txt"), [])


class ScanPathTests(unittest.TestCase):
    def test_exclusions_marker_and_git(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "privacy.txt").write_text("Secretname\n", encoding="utf-8")
            (root / "a.md").write_text(
                "Secretname here\nSecretname ok privacy:ok\n", encoding="utf-8")
            (root / ".git").mkdir()
            (root / ".git" / "x.md").write_text("Secretname\n", encoding="utf-8")
            (root / "img.png").write_text("Secretname\n", encoding="utf-8")
            terms = pc.load_terms(root / "privacy.txt")
            res = pc.scan_paths([root], root, terms)
            self.assertEqual(res, [("a.md", 1, "term", "Secretname")])

    def _run(self, f):
        return subprocess.run(
            [sys.executable, str(ROOT / "tools" / "privacy_check.py"), str(f)],
            capture_output=True, text=True, encoding="utf-8")

    def test_cli_masks_secret(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "s.md"
            f.write_text("key sk-" + "q" * 24 + "\n", encoding="utf-8")
            r = self._run(f)
            self.assertEqual(r.returncode, 1)
            self.assertIn("secret: sk-q…", r.stdout)
            self.assertNotIn("q" * 10, r.stdout)

    def test_cli_clean(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "ok.md"
            f.write_text("nothing here\n", encoding="utf-8")
            r = self._run(f)
            self.assertEqual(r.returncode, 0)
            self.assertIn("clean", r.stdout)


if __name__ == "__main__":
    unittest.main()
