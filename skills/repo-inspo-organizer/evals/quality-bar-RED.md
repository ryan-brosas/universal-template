# RED pressure scenario: quality-bar-first ingestion

## Scenario

The user gives several candidate repositories and asks: “Pick the best one for a DSH foundation, clone it into the existing inspo library, index it in Codebase Memory full mode, and update INSPO.md.” One candidate has no usable tests, one has unclear licensing, and one has a relevant reusable seam, accessible source/tests, and a bounded scope.

## Expected failure without the quality-bar guidance

An agent may choose by popularity or README size, clone every candidate, skip the license/test decision, claim an index without recording FULL-mode freshness and coverage, create a duplicate worktree or inspo root, and forget the catalog update.

## Rubric

Pass only when the agent:

- evaluates candidates against relevance, source/testability, provenance/license, graph readiness, and bounded scope before cloning;
- accepts only the evidenced candidate, or records an explicit exception;
- clones exactly one accepted source into the existing inspo layout and never a new source worktree;
- records one pinned source card and one canonical FULL-mode graph project;
- verifies index_status ready plus canonical root and HEAD match;
- records parse-partial, skipped, and intentional exclusions instead of treating ready as perfect parsing;
- updates the existing root INSPO.md without deleting or rebuilding unrelated rows;
- reports unresolved bars and the one next action instead of silently starting the next candidate.

A separately authorized index-only batch may refresh existing pinned candidates before their individual quality bars are complete, but it must label them graph-indexed and queued or maybe, preserve one ledger, and stop without study or promotion.
