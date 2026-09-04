<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->


# TanStack Query: async-state cache kernel foundation

## Use this for
Use when building any server-state/async-state layer: request de-duplication and promise sharing, retry with offline/focus pause semantics, cache GC tied to subscriber counts, structural sharing over JSON results, cross-framework store bindings, or porting query/mutation machinery into another runtime. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./retryer-pause-resume-machine.md` — how does one retry loop serve online/offline + focus pause without losing retries?
- `./query-fetch-dedup-revert-ladder.md` — when does a concurrent fetch reuse the in-flight promise vs silently cancel vs revert?
- `./query-dispatch-reducer.md` — which state fields does each action own, and what does an error do to existing data?
- `./fetch-state-optimistic-transitions.md` — how does the same fetchState helper drive real transitions and render-time optimism?
- `./hash-key-canonical-json.md` — why is `{a:1,b:2}` and `{b:2,a:1}` the same cache entry?
- `./partial-match-key-prefix.md` — what makes array/object keys match by prefix for invalidation?
- `./replace-equal-depth-sharing.md` — how does referential identity survive refetches?
- `./replace-data-structural-gate.md` — when is structural sharing skipped, customized, or crash-guarded?
- `./notify-manager-transaction-batch.md` — why can notifications never fire synchronously mid-mutation?
- `./removable-gc-refcount.md` — what keeps live entries alive and evicts exactly when idle?
- `./focus-online-lazy-listener.md` — how do global event sources stay free until first subscribe?
- `./timeout-manager-provider-audit.md` — how are thousands of timers kept swappable and auditable?
- `./query-cache-build-remove-guard.md` — what stops removal races from deleting a newer replacement?
- `./client-defaults-dependent-options.md` — which defaults depend on other options, and why is `_defaulted` idempotent?
- `./observer-result-select-placeholder-memo.md` — how do select and placeholderData stay stable across renders?
- `./tracked-prop-proxy-gate.md` — how do unused result properties stop triggering re-renders?
- `./mutation-callback-await-ledger.md` — in what exact order do mutation callbacks run, and who owns their errors?
- `./mutation-scope-serialization.md` — how do scoped mutations queue-and-chain instead of racing?
- `./infinite-page-directional-behavior.md` — how does one behavior hook produce forward/backward/refetch page walks?
- `./hydration-newer-wins-promise.md` — how does server state merge without clobbering fresher client data or in-flight promises?
- `./streamed-query-refetch-mode.md` — how does an AsyncIterable stream land in the cache chunk-by-chunk?
- `./use-base-query-render-contract.md` — what must a framework binding do in render vs effect order?

## Capsule map
- **Fetch retry kernel** — `retryer-pause-resume-machine`: single-loop retryer whose pause() promise resolves only through continueFn gated on focus+network+canRun; cancelRetry latches across sleep windows.
- **Fetch dedup ladder** — `query-fetch-dedup-revert-ladder`: idle/rejected-check, cancelRefetch silent-cancel, continueRetry piggyback, revert-on-unmount, settled-retryer drop in finally.
- **Query reducer** — `query-dispatch-reducer`: action table where error flips status to 'error', bumps errorUpdateCount, unconditionally sets isInvalidated, and never touches data.
- **Optimistic fetchState** — `fetch-state-optimistic-transitions`: shared helper computing paused-vs-fetching from networkMode and pending-only resets, reused by createResult's `_optimisticResults`.
- **Cache hashing** — `hash-key-canonical-json`: JSON.stringify with sorted-key replacer; object key ORDER is not identity.
- **Key prefix matching** — `partial-match-key-prefix`: recursive b-shorter-than-a walk; arrays positional, objects subset.
- **Structural sharing** — `replace-equal-depth-sharing`: depth-capped (500) copy-on-write diff returning the ORIGINAL root when nothing changed.
- **Sharing policy gate** — `replace-data-structural-gate`: function override > default sharing > false bypass, dev-mode JSON-serializability guard that rethrows.
- **Notify batching** — `notify-manager-transaction-batch`: transaction counter defers callbacks into one systemSetTimeoutZero flush wrapped in batchNotifyFn.
- **GC base class** — `removable-gc-refcount`: scheduleGc/clearGcTimeout around optionalRemove; max-monotonic gcTime; server default Infinity.
- **Lazy env listeners** — `focus-online-lazy-listener`: onSubscribe installs the platform listener once; last unsubscribe tears it down; setFocused change-detection.
- **Timer backend** — `timeout-manager-provider-audit`: wrapper-function provider references, ManagedTimerId union, late-provider-switch warning, deliberate non-mediated setTimeout(0).
- **Cache store guards** — `query-cache-build-remove-guard`: build dedupes by hash; remove destroys then deletes only if identical; notify always.
- **Client option resolution** — `client-defaults-dependent-options`: three-layer spread plus dependent rules (refetchOnReconnect←networkMode, throwOnError←suspense, enabled←skipToken, networkMode←persister).
- **Observer result factory** — `observer-result-select-placeholder-memo`: placeholder memo skips re-select; select memo keyed on data identity + fn identity; selectError lifecycle.
- **Property tracking** — `tracked-prop-proxy-gate`: render-time Proxy records accessed props; notification fires only when a tracked prop actually changed.
- **Mutation ledger** — `mutation-callback-await-ledger`: config→hook await chain on success, try/void-reject isolation on error paths, success dispatched AFTER user callbacks.
- **Scope serialization** — `mutation-scope-serialization`: scope-id buckets; canRun = no earlier pending; runNext continues the next paused mutation in finally.
- **Infinite behavior** — `infinite-page-directional-behavior`: onFetch swaps context.fetchFn for a page walker driven by meta.direction; null param stops; maxPages trims both planes together.
- **Hydration merge** — `hydration-newer-wins-promise`: dehydratedAt/dataUpdatedAt newer-wins with fetchStatus stripped; pending queries carry promises consumed via initialPromise; sync-resolution fast path.
- **Streamed query** — `streamed-query-refetch-mode`: reset clears to resetState pre-stream; append setQueryData per chunk; replace buffers until stream end; consume-aware signal breaks the loop.
- **Framework binding** — `use-base-query-render-contract`: getOptimisticResult before useSyncExternalStore, effect-only setOptions, suspense throws the optimistic promise, trackResult wraps the return.

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
TanStack Query (`MIT`), `main@bc423b37ef7fa2a34cfc7286945fd640d74b4071`; Codebase Memory project `ext-ui-tanstack-query` (FULL mode ready, head==base zero drift, 13,080n/31,183e, generation 2026-08-23T11:13Z; parse_partial ×6 confined to example HTML templates, pnpm-lock, and one react-query barrel line — none cited).

## Full view (memory graph)
Revalidate `ext-ui-tanstack-query` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. All 22 cited symbols resolve `^exact$` via search_graph name_pattern against this project; direct tests live in `packages/query-core/src/__tests__/<module>.test.tsx(x)` (24 files, one-per-module coverage).

## Boundaries
Adopt the framework-free contracts: retryer pause/resume, dispatch reducers, hashing/sharing, batching, GC, observer result math, hydration merge, infinite/stream behaviors (all pure TypeScript, zero dependencies in @tanstack/query-core). Adapt host integration points: timeoutManager/notifyManager/environmentManager injection surfaces, focusManager/onlineManager window wiring, persister hooks, and the react-query binding (substitute your host's subscription/effect primitives following use-base-query-render-contract ordering). Omit product surface: devtools packages, persist-client storage adapters, codemods, angular/svelte/vue/solid/lit adapter bodies (contract twins of the mined kernels), and examples/integrations fixtures.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`client-defaults-dependent-options.md`](./client-defaults-dependent-options.md)
- [`fetch-state-optimistic-transitions.md`](./fetch-state-optimistic-transitions.md)
- [`focus-online-lazy-listener.md`](./focus-online-lazy-listener.md)
- [`hash-key-canonical-json.md`](./hash-key-canonical-json.md)
- [`hydration-newer-wins-promise.md`](./hydration-newer-wins-promise.md)
- [`infinite-page-directional-behavior.md`](./infinite-page-directional-behavior.md)
- [`mutation-callback-await-ledger.md`](./mutation-callback-await-ledger.md)
- [`mutation-scope-serialization.md`](./mutation-scope-serialization.md)
- [`notify-manager-transaction-batch.md`](./notify-manager-transaction-batch.md)
- [`observer-result-select-placeholder-memo.md`](./observer-result-select-placeholder-memo.md)
- [`partial-match-key-prefix.md`](./partial-match-key-prefix.md)
- [`query-cache-build-remove-guard.md`](./query-cache-build-remove-guard.md)
- [`query-dispatch-reducer.md`](./query-dispatch-reducer.md)
- [`query-fetch-dedup-revert-ladder.md`](./query-fetch-dedup-revert-ladder.md)
- [`removable-gc-refcount.md`](./removable-gc-refcount.md)
- [`replace-data-structural-gate.md`](./replace-data-structural-gate.md)
- [`replace-equal-depth-sharing.md`](./replace-equal-depth-sharing.md)
- [`retryer-pause-resume-machine.md`](./retryer-pause-resume-machine.md)
- [`streamed-query-refetch-mode.md`](./streamed-query-refetch-mode.md)
- [`timeout-manager-provider-audit.md`](./timeout-manager-provider-audit.md)
- [`tracked-prop-proxy-gate.md`](./tracked-prop-proxy-gate.md)
- [`use-base-query-render-contract.md`](./use-base-query-render-contract.md)
