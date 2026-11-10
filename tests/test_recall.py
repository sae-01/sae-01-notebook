import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import recall  # noqa: E402

DOC = """# 2026-11-10

## Session 1
- Fixed the windows console encoding bug
  by forcing utf-8 output.
- Wrote the wake script.

A plain paragraph about tasks
spanning two lines.

## Session 2
- Added unittest tests.
"""


class TokenizeTests(unittest.TestCase):
    def test_lowercase_stopwords_stem(self):
        self.assertEqual(recall.tokenize("The Tests are Testing"), ["test", "test"])

    def test_short_words_not_overstemmed(self):
        self.assertEqual(recall.tokenize("is gas bus"), ["gas", "bus"])

    def test_word_forms_meet(self):
        # Found by a recall test (2026-11-10): these pairs failed to match.
        for group in (["line", "lines"], ["note", "notes", "noted"],
                      ["week", "weekly"], ["class", "classes"],
                      ["summarize", "summarized"]):
            stems = {recall.stem(w) for w in group}
            self.assertEqual(len(stems), 1, f"{group} -> {stems}")


class ChunkTests(unittest.TestCase):
    def setUp(self):
        self.chunks = recall.chunk_markdown(DOC, "j.md")

    def test_chunk_boundaries(self):
        texts = [c.text for c in self.chunks]
        self.assertEqual(len(texts), 4)
        self.assertIn("by forcing utf-8 output.", texts[0])  # continuation kept
        self.assertTrue(texts[2].startswith("A plain paragraph"))

    def test_fenced_code_skipped(self):
        chunks = recall.chunk_markdown("- real\n```\nsecret example\n```\n- after\n", "f.md")
        self.assertEqual([c.text for c in chunks], ["- real", "- after"])

    def test_headings_and_lines(self):
        first, _, para, last = self.chunks
        self.assertEqual((first.heading, first.line), ("Session 1", 4))
        self.assertEqual(para.line, 8)
        self.assertEqual(last.heading, "Session 2")


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.engine = recall.BM25(recall.chunk_markdown(DOC, "j.md"))

    def test_best_match_first(self):
        hits = self.engine.search("encoding problem")
        self.assertTrue(hits)
        self.assertIn("encoding", hits[0][1].text)

    def test_heading_words_searchable(self):
        hits = self.engine.search("session 2 tests")
        self.assertEqual(hits[0][1].heading, "Session 2")

    def test_no_match(self):
        self.assertEqual(self.engine.search("zebra"), [])

    def test_empty_corpus(self):
        self.assertEqual(recall.BM25([]).search("anything"), [])


class LoadTests(unittest.TestCase):
    def test_load_markdown_from_tree(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "memory" / "journal").mkdir(parents=True)
            (root / "memory" / "journal" / "x.md").write_text("- alpha beta\n", encoding="utf-8")
            (root / "TASKS.md").write_text("- [ ] T1 gamma\n", encoding="utf-8")
            (root / "other.md").write_text("- ignored\n", encoding="utf-8")
            sources = {c.source for c in recall.load_markdown(root)}
            self.assertEqual(sources, {"memory/journal/x.md", "TASKS.md"})


if __name__ == "__main__":
    unittest.main()
