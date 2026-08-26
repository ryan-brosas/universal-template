---
name: repo-inspo-organizer
description: Organize inspiration checkouts and cloned folders under work/inspo.
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

## When to Use

- Place a requested inspiration repository in the existing work/inspo library.
- Repair or organize an already-cloned inspiration folder.
- Create or repair the source sidecar and catalog path entry.
- Confirm where an inspiration checkout lives and whether it is a worktree.

Do not use for: Codebase Memory indexing, graph queries, repository learning, source
tests, capsule writing, DSH project implementation, foundation-skill creation, or
Factory/cron automation.

## Canonical placement

The user-facing path is /home/utopia/work/inspo/; in this environment it resolves
to the existing canonical library /mnt/hdd/utopia/inspo/. Resolve the path instead
of assuming either spelling. Preserve the library's existing flat or nested layout.
For the established flat layout, a source is:

    <inspo-root>/<slug>/              pinned inspiration checkout
    <inspo-root>/<slug>.source.yml    provenance sidecar
    <inspo-root>/<slug>-work/         optional organization record
    <inspo-root>/<slug>-study/        existing study data; do not create for layout alone

work/inspo is not a DSH task worktree. An inspiration checkout normally reports
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
   ~/.dsh/template/source.yml, filling path, URL, ref, HEAD, role, and unresolved
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
- No edits under .dsh/skills/ or an active DSH project.
- No Factory task creation, recurring prompts, cron lanes, or autonomous continuation.
- No secrets, .env files, generated dependencies, or copied source trees in records.
- No new Git worktree for an inspiration checkout.

## Verification

A layout operation is complete only when the reported path exists, the source
sidecar points to that exact checkout, the catalog pointer is scoped, and the
checkout's Git worktree status has been checked. If any identity or destination
fact is unknown, report it as unresolved and stop.

## References

- references/folder-layout.md — ownership and existing-library placement.
- references/source-card.yml — pointer to the canonical sidecar template.
