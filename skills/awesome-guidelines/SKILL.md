---
name: awesome-guidelines
description: "Use when a practices leaf or question points at a specific awesome-guidelines style capsule or learning note - archived cold library; the ingestion pipeline is retired, so load only to read a cited capsule."
invocation: manual
disable-model-invocation: true
x-archive: true
---

# Awesome Guidelines, archived style-capsule library

> **Archived (2026-09):** the ingestion pipeline (learn → note → capsule → wire skill) is retired. Useful repositories become project-local `reference/<repo>/` checkouts; accumulated foundations live under `skills/*-foundation` (create only when reusable understanding is earned). This skill stays as the cold library behind the `*-coding-practices` leaves; its `references/` capsules are still their content source. Load it only to read a specific capsule or learning note; do not run new ingestion.

## Core Principle

This skill is an archive, not a procedure. Its `references/` capsules are the
content source behind the `*-coding-practices` leaves; nothing new is ingested.
The filesystem is the index, there is no catalog to maintain.

## When to Use / NOT

- **Use when:** a practices leaf or a question cites a specific capsule or
 learning note under `references/`, open exactly that file.
- **NOT when:** adopting a new external repository, use reference-first
 (`reference-driven-development`).
- **NOT when:** a stack capsule under `skills/*-foundation` covers the topic, load that instead.

## Workflow

1. Open the cited capsule by filename. Find candidates with
 `ls references/` or ripgrep over that
 directory (capsule names are `<lang>-style-<topic>.md` and
 `<topic>-style-learning-note.md`).
2. Apply it through the practices leaf that owns the topic.
3. Do not add rows, notes, or capsules; the pipeline is retired.

## Red Flags

- Running the old learn → note → capsule → wire-skill pipeline.
- Writing new learning notes or ingestion-index rows.
- Treating a capsule as current best practice without checking the practices
 leaf that superseded it.

## Verification

- The cited capsule exists on disk and no new files were added.
- The consuming practices leaf, not this archive, drove the change.
