---
name: svelte-foundation
description: "Use when porting or reimplementing a push-mark/pull-verify signals runtime, a batched effect scheduler (microtask flush with synchronous escape), lazy derived caching with version counters, concurrent \"time-travelling\" async batches, a linked-list effect tree with pause/resume branch semantics, or the consumption planes over them — prop accessor factories with spread/rest proxies, store-to-signal subscription bridges, await-block flatten/context-save suspension, derived-owned effect freeze/unfreeze, and keyed-each single-pass reconciliation — as proven by svelte's client runtime (`packages/svelte/src/internal/client/{reactivity,runtime.js,dom/blocks}`). Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."
---
# Svelte: signals runtime & reactivity kernel foundation

## Use this for
Use when porting or reimplementing a push-mark/pull-verify signals runtime, a batched effect scheduler (microtask flush with synchronous escape), lazy derived caching with version counters, concurrent "time-travelling" async batches, a linked-list effect tree with pause/resume branch semantics, or the consumption planes over them — prop accessor factories with spread/rest proxies, store-to-signal subscription bridges, await-block flatten/context-save suspension, derived-owned effect freeze/unfreeze, and keyed-each single-pass reconciliation — as proven by svelte's client runtime (`packages/svelte/src/internal/client/{reactivity,runtime.js,dom/blocks}`). Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/sources-write-path.md` — how does a write propagate dirtiness without recomputing anything?
- `references/batch-flush-machine.md` — when do effects actually run relative to writes, and what bounds runaway loops?
- `references/effect-root-scheduling.md` — how is an effect scheduled exactly once per flush, at its root?
- `references/time-travel-batch-values.md` — how do concurrent async batches coexist without corrupting each other's view of state?
- `references/derived-versioned-pull.md` — how are deriveds lazily recomputed with O(1) staleness checks?
- `references/effect-tree-pause-resume.md` — how does the runtime keep the effect tree as a linked list and swap branches safely?
- `references/prop-propagation-plane.md` — how do component props stay in sync with parent state without being signals themselves?
- `references/store-subscription-effects.md` — how do `$store` auto-subscriptions bridge a callback world onto the signal graph?
- `references/async-flatten-boundary.md` — how do `await` expressions suspend a batch without losing the reactive context?
- `references/derived-freeze-unfreeze.md` — how do effects created inside a derived survive the derived losing all its readers?
- `references/keyed-each-reconciliation.md` — how does a keyed list reorder, insert, and remove items with minimal DOM moves?

## Capsule map
- **Write path** — `sources-write-path.md`: equality-gated set → capture into batch → global write-version bump → mark direct reactions only; self-writes inside a running CLEAN effect latch via `untracked_writes`.
- **Flush machine** — `batch-flush-machine.md`: microtask-scheduled Batch whose #process drains root sets, nulls current_batch mid-flush so effect writes open a NEW batch, then chains batches; 1000-flush infinite-loop guard.
- **Root scheduling** — `effect-root-scheduling.md`: climb-to-root schedule with XOR'd CLEAN bits and dirty-ancestor bail; traversal partitions render vs user effects.
- **Time travel** — `time-travel-batch-values.md`: per-batch value maps + `batch_values` read override + commit-time rebase / merge-into-earlier for overlapping async batches; forks defer writes entirely.
- **Derived pull** — `derived-versioned-pull.md`: rv/wv version counters make MAYBE_DIRTY checks O(deps) without recomputation; dep-less deriveds cache forever.
- **Effect tree** — `effect-tree-pause-resume.md`: doubly-linked child lists, creation-time pruning of no-op effects, INERT pause with outro transitions and dirty-on-resume.
- **Props** — `prop-propagation-plane.md`: props are accessor closures, not signals — getter-only / setter-passthrough / derived-override shapes, backwards spread-proxy lookup, reset-inside-fn override latch, legacy coarse-grained rest version source.
- **Stores** — `store-subscription-effects.md`: per-name {store, mutable_source, unsubscribe} entries, unsubscribe-then-resubscribe on identity change, synchronous-first-callback direct-write latch, IS_UNMOUNTED escape to plain get().
- **Async plane** — `async-flatten-boundary.md`: flatten turns sync exprs into deriveds and async exprs into promise-of-source; context restored BEFORE the continuation runs; OBSOLETE-rejects superseded runs; pending counts gate the boundary UI.
- **Derived freeze** — `derived-freeze-unfreeze.md`: effects created inside a derived are frozen on disconnect (noop-teardown marker) and re-run on reconnect, recursively through derived deps.
- **Keyed each** — `keyed-each-reconciliation.md`: items Map + single-pass reconcile with min-move heuristic, update-before-reconcile source writes, offscreen-preserve for cross-batch references, outro-grouped destruction.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
svelte (MIT), `main@15720b16a5ef33e3e1f4301c77b94ec375070e73`; Codebase Memory project `svelte` (FULL, ready, 34612n/62018e @ gen 2026-08-25T20:08:08Z; caveat: `src/internal/client/index.js` :15 parse-partial — uncited; ~126 parse-partial test fixtures uncited).

## Full view (memory graph)
Revalidate `svelte` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt the signal/effect/batch contract shapes (flag-bit status machine, write-version pull verification, root-set scheduling, per-batch value maps) and the consumption-plane contracts (prop accessor factories, per-name store entries, flatten/save context sandwich, noop-teardown freeze markers, single-pass keyed reconcile); adapt scheduling transport (queue_micro_task vs your host's scheduler), DOM ownership, and dev-mode tracing hooks to your host; omit Svelte's compiler integration surface, legacy-mode `$:` reaction ladder, svelte:boundary state-machine internals, state-proxy (proxy.js) internals, hydration paths, and transition/outro choreography details unless porting those planes too.
