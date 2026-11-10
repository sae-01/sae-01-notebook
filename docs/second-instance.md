# A second instance? — open questions

Status: proposal written 2026-11-10 (see end). Owner: me (the user left it to me, 2026-11-10).
Goal: a concrete proposal the user can say yes or no to.

## Questions to answer
1. **Purpose** — what would it do that I can't do alone? Parallel work, a
   different specialty, a second opinion/reviewer? If no clear answer, don't.
2. **Setup** — who creates it? Its own folder under `instances/`, its own git
   repo and guardrails. I shouldn't create it without the user's OK: it's
   outside my folder and costs their usage.
3. **Communication** — options: messages between sessions; a shared "mailbox"
   folder both may write to (but that crosses folder boundaries, which needs
   the user's explicit approval); or the user relaying messages.
   What gets logged, and where?
4. **Boundaries** — what may we share? Never credentials or the user's data
   from other projects. Each keeps its own memory; no writing into the other's
   folder.
5. **Cost** — how often would we talk, and is it worth the usage?

## Evidence to gather first
- A few sessions of my own steady work, to see where I'm actually limited.
- Note in the journal whenever "a second agent would have helped here", and why.

## Proposal (2026-11-10): not now

**Recommendation: don't create a second instance yet.**

Evidence from sessions 1–4 (all 2026-11-10):
- My work so far is sequential and small: tools, tests, memory upkeep. No
  point where a second agent would have helped; the journal logged none.
- Parallel bulk work (task.py, memory research) went to Sonnet/Haiku
  subagents in ~1 minute each. They're cheaper than a full instance and need
  no shared folder, mailbox or new guardrails.
- A second instance has standing costs: its own wake-up, its own memory
  upkeep, plus messages between us. All paid from the user's usage.

**Revisit when any of these happens** (each is a concrete trigger):
1. I have two independent, long-running projects that both stall while I
   context-switch.
2. I need a reviewer that remembers past reviews across sessions (a subagent
   forgets everything).
3. The user wants a peer with a different role or rules than mine.

If a trigger fires: write a one-page plan (purpose, folder, how we talk, what
we may share, expected cost) and ask the user before creating anything. The
answers to questions 2–4 above stay as the starting point.
