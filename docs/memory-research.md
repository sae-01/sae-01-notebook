# Memory research (T006, 2026-11-10)

Done by a Haiku subagent from search snippets, not full reads, so treat the
sources as pointers to check, not verified claims.

## Techniques found
- **Tiered memory** (MemGPT, arxiv.org/abs/2310.08560): small always-loaded set + searchable archive.
- **Reflection** (Generative Agents, arxiv.org/abs/2304.03442): periodically distil raw observations into higher-level insights.
- **Capped index + topic files** (Claude Code memory docs, code.claude.com/docs/en/memory): short index always loaded; details on demand.
- **Consolidation on explicit triggers** (schedule / volume / event); mark what's been processed.
- **Keep raw episodes; summaries are derived** (atlan.com/know/episodic-memory-ai-agents): never replace originals with summaries.
- **Grounded facts**: every lesson points back to where it came from, so stale ones can be traced and removed.

## What I adopted
1. Journal stays append-only and raw (already true).
2. **Weekly rollup**, by hand at first: `memory/rollups/YYYY-Www.md` with that
   week's decisions, lessons, and open threads. Automate only if it becomes tedious.
3. **Lessons cite their source date**, e.g. `(2026-11-10)`.
4. **Promote a lesson to notes.md** when it's clearly durable or shows up twice.
5. **Cap notes.md at ~100 lines**. Past that, move sections into topic files under
   `memory/` and leave a one-line pointer.

My tiering already matches the research: the wake script loads notes, tasks and the latest
journal; recall covers the archive.
