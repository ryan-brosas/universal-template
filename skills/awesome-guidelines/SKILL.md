---
name: awesome-guidelines
description: "Use when a practices leaf or question points at a specific awesome-guidelines style capsule or learning note - archived cold library; the ingestion pipeline is retired, so load only to read a cited capsule."
disable-model-invocation: true
x-archive: true
---

# Awesome Guidelines, archived style-capsule library

> **Archived (2026-09):** the ingestion pipeline (learn → note → capsule → wire skill) is retired. The catalog is reference-first: useful repositories become `reference/<repo>/` checkouts, and foundation creation is frozen with no new foundations (legacy `*-foundation` leaves sit cold in `foundation-pack/`). This skill stays as the cold library behind the `*-coding-practices` leaves, its `references/` capsules are still their content source. Load it only to read a specific capsule or learning note; do not run new ingestion.

## Core Principle

This skill is an archive, not a procedure. Its `references/` capsules are the
content source behind the `*-coding-practices` leaves; nothing new is ingested.
The filesystem is the index, there is no catalog to maintain.

## When to Use / NOT

- **Use when:** a practices leaf or a question cites a specific capsule or
 learning note under `references/`, open exactly that file.
- **NOT when:** adopting a new external repository, use reference-first
 (`reference-driven-development`).
- **NOT when:** a stack capsule in `foundation-pack/` covers the topic, load that instead.

## Workflow

1. Open the cited capsule by filename. Find candidates with
 `ls ~/.agents/skills/awesome-guidelines/references/` or
 `python3 scripts/skill-catalog.py search "<topic>"` (capsule names are
 `<lang>-style-<topic>.md` and `<topic>-style-learning-note.md`).
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
