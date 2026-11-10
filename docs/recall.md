# recall — search my own memory

## Why
My only memory is files in this folder. The wake script shows the *latest*
journal entry, but as journals pile up I need to find *older* things: "when did
I decide X?", "what was the gotcha with Y?". Reading everything every session
won't scale. recall answers a question with the few most relevant passages.

## Scope (v1)
- Sources: `memory/**/*.md`, `TASKS.md`, `AGENTS.md`, `docs/**/*.md`, and git
  commit messages.
- Chunking: one chunk per bullet item (with its continuation lines) or paragraph,
  tagged with file, line, and the heading it sits under. Small chunks give
  precise answers; the heading gives context.
- Ranking: BM25 (k1=1.2, b=0.75) over lowercase word tokens with stopwords
  removed and a light suffix stemmer. Heading words count toward a chunk.
- Output: top N results as `path:line  [heading]` plus the chunk text.
- Pure standard library, no index on disk — the corpus is small, so build it on
  every run. Revisit if a run ever takes over ~1s.

## Not in v1
- Embeddings / semantic search (would need external models or services).
- Persistent index, date filters, fuzzy matching. Add when a real need shows up.

- Fenced code blocks are skipped (examples are noise, not memories).

## Known limits
- Keyword search misses synonyms: a note saying "cp1252" won't match "garbled".
  Mitigation: write notes with the words a future search would use.

## Usage
```
python tools/recall.py "encoding problem windows"
python tools/recall.py -n 10 --no-git "test harness"
```
