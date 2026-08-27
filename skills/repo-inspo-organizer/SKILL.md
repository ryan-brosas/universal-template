---
name: repo-inspo-organizer
description: "Use when placing or repairing an inspiration repository checkout under the shared inspo library — canonical placement, source sidecar, catalog pointer, and worktree identity checks. Host-neutral; does not index, study, or promote the repo."
---

# Repository Inspo Organizer

This skill owns only the physical organization of inspiration repositories and their
cloned folders. It keeps the existing work/inspo library predictable; it does not
ingest, index, study, translate, or promote a repository.

<HARD-GATE>
Before any placement or source-folder mutation, run pwd, resolve the existing
inspiration root with readlink -f, and inspect its current catalog/layout. Never
create a new inspiration root, duplicate an existing checkout, or create a Git
worktree for an inspiration source.
</HARD-GATE>

## Core Principle

This skill owns only the physical organization of inspiration repositories and their
cloned folders — canonical placement, source sidecar, catalog pointer, and worktree
identity checks. It keeps the existing work/inspo library predictable; it does not
ingest, index, study, translate, or promote a repository.

## When to Use

- Place a requested inspiration repository in the existing work/inspo library.
- Repair or organize an already-cloned inspiration folder.
- Create or repair the source sidecar and catalog path entry.
- Confirm where an inspiration checkout lives and whether it is a worktree.

Do not use for: Codebase Memory indexing, graph queries, repository learning, source
tests, capsule writing, active project implementation, foundation-skill creation, or
scheduled-task/cron automation.

## Workflow

Locate the library → identify the source → place or repair → verify identity → record
the sidecar → update catalog pointers → report and stop. The full steps with completion
conditions are in `Procedure` below.

## Canonical placement

The user-facing path is /home/utopia/work/inspo/; in this environment it resolves
to the existing canonical library /mnt/hdd/utopia/inspo/. Resolve the path instead
of assuming either spelling. Preserve the library's existing flat or nested layout.
For the established flat layout, a source is:

    <inspo-root>/<slug>/              pinned inspiration checkout
    <inspo-root>/<slug>.source.yml    provenance sidecar
    <inspo-root>/<slug>-work/         optional organization record
    <inspo-root>/<slug>-study/        existing study data; do not create for layout alone

work/inspo is not a task worktree of any agent CLI. An inspiration checkout normally reports
is_worktree=false.

## Procedure

1. Locate the library. Run pwd; resolve /home/utopia/work/inspo with readlink -f;
   inspect existing INSPO.md and QUEUE.md before writing. Completion: one existing
   absolute inspo root is recorded.
2. Identify the source. Determine its slug, URL, intended ref, and whether the
   requested destination already exists. Completion: no duplicate path is ambiguous.
3. Place or repair. If absent, clone directly into the existing inspo root's
   <slug>/ directory. If present, inspect and repair its organization in place.
   Never create a source worktree, second checkout, or second inspo root.
4. Verify identity. Confirm remote, branch/ref, resolved HEAD, current path, clean
   state when relevant, and is_worktree=false. Completion: the checkout's physical
   identity is recorded, not inferred from a template.
5. Record the sidecar. Create or update <slug>.source.yml from
   ~/.agents/templates/source.yml, filling path, URL, ref, HEAD, role, and unresolved
   fields honestly. Do not claim graph, study, test, license, or promotion status
   that was not separately established.
6. Update catalog pointers. Make the smallest scoped change to existing INSPO.md or
   QUEUE.md entries needed to point at the organized source. Do not replace either
   catalog wholesale and do not add learning conclusions.
7. Report and stop. Return the canonical path, alias if any, sidecar path, checkout
   identity, worktree result, catalog files touched, and unresolved organization
   issues. Hand off graph or learning work to its separate skill.

## Non-negotiable boundaries

- No mcp__codebase-memory__ calls.
- No source reads for learning, graph status, study notes, or foundation capsules.
- No edits under the shared skill catalog (~/.agents/skills/) or an active project of the driving CLI.
- No scheduled-task creation, recurring prompts, cron lanes, or autonomous continuation.
- No secrets, .env files, generated dependencies, or copied source trees in records.
- No new Git worktree for an inspiration checkout.

## Red Flags

- Creating a new inspiration root, duplicating an existing checkout, or creating a Git
  worktree for an inspiration source.
- `mcp__codebase-memory__` calls, source reads for learning, or foundation capsule
  writing from this skill.
- Edits under the shared skill catalog (`~/.agents/skills/`) or an active project of
  the driving CLI.
- Replacing INSPO.md or QUEUE.md wholesale instead of making the smallest scoped
  pointer change.
- Claiming graph, study, test, license, or promotion status that was not separately
  established.

## Verification

A layout operation is complete only when the reported path exists, the source
sidecar points to that exact checkout, the catalog pointer is scoped, and the
checkout's Git worktree status has been checked. If any identity or destination
fact is unknown, report it as unresolved and stop.

## Skill Result Contract

```
<skill_result>
  <skill><name></skill>
  <status>success|partial|blocked|failure</status>
  <evidence>…</evidence>
  <artifacts>…</artifacts>
  <risks>…</risks>
</skill_result>
```

## References

- `references/folder-layout.md` — ownership and existing-library placement: the resolved inspo root, per-item location rules, and the flat-layout source shape.
- references/source-card.yml — pointer to the canonical sidecar template (`~/.agents/templates/source.yml`) with host-mirror drift rules.
- `references/pi-template-workflow.md` — pi-template-derived source work records: one source, one durable record, graph-refresh lane, read-only checkout rule.
- `references/quality-bar.md` — repository selection quality bar to apply before cloning a candidate into the inspiration library.
- `references/study-pass-template.md` — compatibility pointer to the canonical shared study skeletons under `~/.dsh/template/study/` (`00-overview.md` through `04-verification.md`).
