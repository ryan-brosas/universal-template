---
name: svelte-foundation
description: "Use when porting or reimplementing a push-mark/pull-verify signals runtime, a batched effect scheduler (microtask flush with synchronous escape), lazy derived caching with version counters, concurrent \"time-travelling\" async batches, or a linked-list effect tree with pause/resume branch semantics — as proven by svelte's client runtime kernel (`packages/svelte/src/internal/client/reactivity/*` + `runtime.js`). Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."
---
# Svelte: signals runtime & reactivity kernel foundation

## Use this for
Use when porting or reimplementing a push-mark/pull-verify signals runtime, a batched effect scheduler (microtask flush with synchronous escape), lazy derived caching with version counters, concurrent "time-travelling" async batches, or a linked-list effect tree with pause/resume branch semantics — as proven by svelte's client runtime kernel (`packages/svelte/src/internal/client/reactivity/*` + `runtime.js`). Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/sources-write-path.md` — how does a write propagate dirtiness without recomputing anything?
- `references/batch-flush-machine.md` — when do effects actually run relative to writes, and what bounds runaway loops?
- `references/effect-root-scheduling.md` — how is an effect scheduled exactly once per flush, at its root?
- `references/time-travel-batch-values.md` — how do concurrent async batches coexist without corrupting each other's view of state?
- `references/derived-versioned-pull.md` — how are deriveds lazily recomputed with O(1) staleness checks?
- `references/effect-tree-pause-resume.md` — how does the runtime keep the effect tree as a linked list and swap branches safely?

## Capsule map
- **Write path** — `sources-write-path.md`: equality-gated set → capture into batch → global write-version bump → mark direct reactions only; self-writes inside a running CLEAN effect latch via `untracked_writes`.
- **Flush machine** — `batch-flush-machine.md`: microtask-scheduled Batch whose #process drains root sets, nulls current_batch mid-flush so effect writes open a NEW batch, then chains batches; 1000-flush infinite-loop guard.
- **Root scheduling** — `effect-root-scheduling.md`: climb-to-root schedule with XOR'd CLEAN bits and dirty-ancestor bail; traversal partitions render vs user effects.
- **Time travel** — `time-travel-batch-values.md`: per-batch value maps + `batch_values` read override + commit-time rebase / merge-into-earlier for overlapping async batches; forks defer writes entirely.
- **Derived pull** — `derived-versioned-pull.md`: rv/wv version counters make MAYBE_DIRTY checks O(deps) without recomputation; dep-less deriveds cache forever.
- **Effect tree** — `effect-tree-pause-resume.md`: doubly-linked child lists, creation-time pruning of no-op effects, INERT pause with outro transitions and dirty-on-resume.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
svelte (MIT), `main@15720b16a5ef33e3e1f4301c77b94ec375070e73`; Codebase Memory project `svelte` (FULL, ready, 34612n/62018e @ gen 2026-08-25T20:08:08Z; caveat: `src/internal/client/index.js` :15 parse-partial — uncited; ~126 parse-partial test fixtures uncited).

## Full view (memory graph)
Revalidate `svelte` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt the signal/effect/batch contract shapes (flag-bit status machine, write-version pull verification, root-set scheduling, per-batch value maps); adapt scheduling transport (queue_micro_task vs your host's scheduler), DOM ownership, and dev-mode tracing hooks to your host; omit Svelte's compiler integration surface, legacy-mode `$:` semantics, store contracts, and transition/outro choreography details unless porting those planes too.
