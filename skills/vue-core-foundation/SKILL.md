---
name: vue-core-foundation
description: "Use when porting or building a proxy-based fine-grained reactivity kernel: Dep/Link dependency graph, pull-based computed ladder, effect lifecycle & scope disposal, reactive/readonly/collection proxies, array instrumentations, trigger fan-out, refs, and base watch."
disable-model-invocation: true
---
# Vue Core (@vue/reactivity): Proxy Reactivity Kernel Foundation

## Use this for
Porting the Vue 3 reactivity model: version-counted Dep/Link doubly-linked dep graphs, mark-free dirty checking with a globalVersion fast path, batched same-tick notification queues, flag-gated ReactiveEffect run/stop/pause lifecycle with orphan guards, EffectScope trees with O(1) swap-pop removal and async-interleaving-safe `off()`, four-quadrant Proxy handlers (reactive/readonly × deep/shallow) plus get-only collection instrumentation, ARRAY_ITERATE-tracking array method instrumentations with raw-search fallback, the exact trigger expansion table for ADD/SET/DELETE/CLEAR/length, dual-value refs with linked property refs, shallow ref-unwrapping proxies, and the base watch that normalizes ref/reactive/getter/array sources. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/dep-link-graph.md` — how are many-to-many dep↔subscriber edges stored, re-used, and torn down without leaks?
- `references/batch-queue.md` — how are same-tick notifications coalesced, ordered, and drained exactly once?
- `references/effect-lifecycle.md` — what flags/stack discipline keep tracking, recursion, pause, and stop correct?
- `references/computed-pull-model.md` — when does a computed re-evaluate, propagate, and stay cached (chained)?
- `references/effect-scope-tree.md` — how do effects get disposed together, paused/resumed, detached safely?
- `references/base-handlers.md` — how do reads track, writes trigger, and identity checks avoid false triggers?
- `references/reactive-factory.md` — when does a value become a proxy, and which quadrant's proxy comes back?
- `references/collection-instrumentations.md` — how do Map/Set/Weak* become reactive via get-only redirection?
- `references/array-instrumentations.md` — which array methods need ARRAY_ITERATE tracking, raw-search retry, untracked mutations?
- `references/trigger-fanout.md` — which implicit deps (ITERATE/length/array-iterate) must each mutation type wake?
- `references/ref-model.md` — how do refs wrap values, unwrap on set, and link to reactive properties?
- `references/proxy-refs.md` — minimal one-level unwrap proxy with write-through-to-ref semantics.
- `references/base-watch.md` — source normalization + forceTrigger + job gating for watch/watchEffect.

## Capsule map
- **Dependency graph** — `dep-link-graph`: Link nodes shared by two intrusive lists; version-sweep resubscribes only what was read; subscriber-count gates property-dep GC (#11979).
- **Notification queue** — `batch-queue`: depth-counted batch; LIFO push = subscription order out; NOTIFIED latch dedupes; errors deferred to drain end.
- **Effect runner** — `effect-lifecycle`: ACTIVE/RUNNING/TRACKING/PAUSED flag contract; cleanup-before-rerun outside tracking context; stopped-scope construction strips ACTIVE (orphan guard).
- **Computed cache** — `computed-pull-model`: TRACKING&&!DIRTY → globalVersion → isDirty ladder; bump own dep.version only on real change; error path bumps before rethrow.
- **Scope disposal** — `effect-scope-tree`: parent+index registration, copy-before-callback iteration, swap-pop parent unlink, mid-chain prevScope unlink for async resumes.
- **Proxy traps** — `base-handlers`: flag keys answered without Reflect → instrumentations → track(GET) → lazy nested wrap; receiver-identity guard suppresses prototype-shadow triggers.
- **Proxy factory** — `reactive-factory`: admission ladder (proxy-check → skip/non-extensible → memo → COMMON vs COLLECTION) over four WeakMap quadrants.
- **Collections** — `collection-instrumentations`: single get-trap redirect to per-quadrant instrumentations operating on raw prototypes; forward-before-trigger; dual raw/reactive key tracking (#1772/#3602).
- **Arrays** — `array-instrumentations`: whole-read methods take one ARRAY_ITERATE dep; identity searches retry with raw args; push/pop/splice run pauseTracking+batch (#2137); user-subclass escape hatch (#11759).
- **Trigger table** — `trigger-fanout`: SET wakes key only; ADD wakes ITERATE(+length on arrays); DELETE wakes ITERATE; CLEAR wakes all; length write wakes indices ≥ newLength; untracked target still bumps globalVersion.
- **Refs** — `ref-model`: `_rawValue` vs `_value` split gates hasChanged and deep toReactive; ObjectRefImpl has no own dep — reads/writes forward through the source proxy.
- **Shallow unwrap** — `proxy-refs`: two-trap proxy unwrapping one level; non-ref assignment writes into the existing ref; skipped when target already reactive.
- **Watch kernel** — `base-watch`: per-source getter table, forceTrigger for reactive/shallowRef sources, dirty-gated job, sentinel oldValues, cleanupMap drained pre-callback and at stop.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
vue-core (`MIT`), `main@e2bede96134f757aad5c5b33ac9be055022dbfc8` (= origin/main at pass 1); Codebase Memory project `ext-vue-core` root `/mnt/hdd/utopia/inspo/external/vue-core`, branch main, ready FULL mode, 6,073 nodes / 29,037 edges, generation 2026-08-23T10:09:23Z, generation_matches=true; parse_partial ×4 (compiler-sfc/parse.ts, runtime-dom/jsx.ts, vue-compat README, an e2e html — none in cited paths); check_index_coverage no_recorded_issue + metadata_match on all 13 cited paths.

## Full view (memory graph)
Revalidate `ext-vue-core` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. All capsule Retrieve blocks cite project `ext-vue-core`; BM25 search_graph resolves every seam symbol (verified pass 1).

## Boundaries
Adopt the pure kernel contracts above — they are framework-free TypeScript with zero DOM dependencies. Adapt scheduler plumbing (`scheduler`, `augmentJob`, `call`, `onWarn`) to your host's flush/error systems. Omit runtime-core concerns (vdom render effects, component instance wiring, Suspense), compiler packages, SSR/server-renderer, vue-compat shims, and DEV-only debugger hooks unless you ship devtools.
