# Pi-template-derived source work records

This workflow adapts the local pi-template durable-record contract while preserving the existing inspiration library layout. The graph-refresh lane adds a minimal record for already-cloned sources; a full study record is still one source at a time.

## One source, one durable record

Every accepted or graph-refreshed source has one source card and one durable work record. The checkout remains a normal read-only Git repository and is not placed in a new worktree.

For the established flat library:

    shared or checkout-relative work/inspo/
      slug/                    pinned checkout
      slug.source.yml          identity, quality, graph, catalog
      slug-work/               durable record
        state.md
        verification.md
        research.md            when study begins
        plan.md                when study begins
        design.md              when translation begins
      slug-study/              bounded study when activated

For a pre-existing nested library, preserve its slug/repo, source.yml, work, and study shape instead of migrating it.

## Record tiers

| Tier | Required files | Meaning |
|---|---|---|
| graph-only refresh | source.yml, work/state.md, work/verification.md | existing checkout has a verified FULL graph; no study claim |
| active study | graph-only files plus research.md, plan.md, study/00 through 04 | one source is being mapped and studied |
| translation | active study plus design.md or ADR when needed | DSH target seams are explicitly verified, inferred, or unknown |
| promotion | all above plus direct verification and catalog closeout | reuse or implementation may be considered |

## Lifecycle mapping

| Repository-learning step | Durable record | Evidence boundary |
|---|---|---|
| quality-bar choice and source pin | source.yml and optional issue/spec | URL, ref, license, role, named question |
| graph indexing and repository map | state.md, verification.md, and GRAPH-INDEX.md for batches | project/root/HEAD/FULL mode, counts, coverage, logs |
| decisive seam study | research.md and study/01-architecture.md, study/02-decisive-paths.md | source paths, symbols, tests, invariants |
| DSH translation | design.md and study/03-translation.md | keep/adapt/drop and target seam |
| execution order | plan.md and tasks.md | dependencies, conflicts, acceptance checks |
| verification and catalog closeout | verification.md, state.md, QUEUE.md, INSPO.md | commands, results, one next action |

## Batch graph-refresh boundary

A user-authorized batch may reindex multiple existing sources with mcp__codebase-memory__index_repository in FULL mode. It must then revalidate every project with mcp__codebase-memory__index_status(verbose=true), compare canonical root and HEAD, preserve parse-partial/skipped/excluded coverage, and stop. It must not create study conclusions, run all source tests, translate APIs, or promote foundations in the same batch.

## Rules borrowed from pi-template

- Durable records are one directory per source; do not scatter state across unrelated roots.
- state.md is the “you are here” marker and separates observed facts from plans.
- verification.md records actual commands and results; never fill it with assumed passes.
- Optional proposal, design, ADR, and task files are added when the active study warrants them.
- Keep active pointers and progress logs separate from durable evidence.
- Never copy credentials, generated dependencies, or an entire source into notes.
