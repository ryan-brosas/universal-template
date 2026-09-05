---
name: goal-setup
description: "Use when recovery, handoff, compliance, or external coordination needs durable work state that source, Git, the tracker, and session history cannot cheaply preserve."
invocation: manual
disable-model-invocation: true
---

# Goal Setup

A work record preserves expensive-to-reconstruct decisions or next state. Duration,
complexity, or a request to plan does not by itself justify a new artifact.

## Qualification

Inspect current source, tests, project instructions, the authoritative tracker,
and relevant session evidence. Create a record only when these cannot cheaply
support the actual recovery, handoff, compliance, or coordination need, or when
the user or project explicitly requires one. Keep an existing tracker authoritative;
do not mirror its tasks or status in Markdown.

Default to recording a verified pass after implementation. A user, project rule,
or external coordinator may require an earlier record; follow that requirement
rather than imposing a post-code-only workflow. Ordinary planning stays in the
conversation unless an artifact is requested or earned by this boundary.

## Record only what is missing

Use the project’s established location. If none exists, agree on a location rather
than automatically creating a planning directory. A compact record may contain:

- What was verified and the relevant evidence.
- Decisions and meaningful counter-evidence that source alone cannot explain.
- Deliberately omitted or unresolved concerns.
- The next target when recovery or handoff requires it.

Do not copy code, Git status, tracker inventories, or a transcript. Split records
only at a real handoff boundary. Update expensive-to-reconstruct state after
verified work; close the record when its coordination purpose ends. Remove it
only when authorized by project policy or the user. Reusable promotion candidates
may be explicitly routed to `../leverage-capture/SKILL.md`.

## Verification

The record has a named need, an appropriate location, and evidence for its claims.
On resume, consult current source, Git, and the tracker before using historical
notes. No record is the right outcome when existing sources are sufficient.
