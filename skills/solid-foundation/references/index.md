<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->

# SolidJS: Fine-Grained Reactivity Foundation

## Use this for
Porting the SolidJS reactivity model: signals and memos without VDOM, mark-then-run propagation with STALE/PENDING states, lazy topological re-execution, owner-tree disposal with O(1) observer swap-removal, batch/transition shadow values, promise-identity-guarded resources, proxy stores with keyed in-place reconciliation, memo-based control flow (For/Index/Show/Switch/ErrorBoundary/Suspense), the compile-out SSR twin of every primitive, deterministic hydration-id allocation, and streaming fragment serialization. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./signal-core.md` — readSignal's symmetric observers/sourceSlots bookkeeping and last-observer fast path.
- `./write-path.md` — writeSignal marks STALE vs PENDING by purity; never runs work inline; infinite-loop cap.
- `./runtop-pull-ladder.md` — runTop/lookUpstream ancestor walk with ExecCount epoch: topo order without a topo sort.
- `./ownership-disposal.md` — createComputation registration, cleanNode reverse cleanups, slot-swap unsubscription.
- `./effect-tiers.md` — computed (sync) / renderEffect / user-effect tier contract + hydration effect stash.
- `./batch-transitions.md` — outermost-runUpdates batching; transition tValue shadow commit protocol.
- `./resource-fsm.md` — createResource five-state machine, `pr === p` stale-response guard, keep-last-value refresh.
- `./error-boundaries.md` — symbol-keyed context handler lists, deferred synthetic-effect dispatch, handler bubbling.
- `./map-array-diff.md` — mapArray prefix/suffix/backward-map identity diff; indexArray mirror.
- `./time-slice-scheduler.md` — MessageChannel 5ms frame budget scheduler (enableScheduling substrate).
- `./external-source-bridge.md` — composable factory chain wrapping computation fns; transition re-subscription fix.
- `./store-proxy-traps.md` — store get/has traps: lazy per-property equals:false nodes, $TRACK/$RAW fast paths.
- `./store-write-fanout.md` — setProperty ordered notification ($HAS → property → length → $SELF) + updatePath grammar.
- `./reconcile-produce.md` — applyState keyed replace-vs-recurse diff; produce's WeakMap setter proxies.
- `./create-mutable.md` — writable twin: real set/delete traps, batched built-in array methods, prototype-chain setters.
- `./store-server-twin.md` — the signal-free server store: what survives compile-out (guards do).
- `./ssr-shadow-kernel.md` — server reactive.ts deletion list: frozen memos, no-op effects, surviving owner tree.
- `./ssr-streaming.md` — placeholder markers, registerFragment/block serialization, error replay markers.
- `./lazy-component.md` — failure-uncaching load promise across client/hydrate/SSR modes.
- `./show-switch-flow.md` — truthiness-equality condition memos + narrowed-accessor stale-read guards.
- `./suspense-ladder.md` — counter context, parked effects resume, fallback-root flicker latch, SuspenseList orders.
- `./error-boundary-component.md` — boundary-as-memo catching its own children via catchError.
- `./merge-props.md` — last-wins skip-undefined props proxy with live getters; function sources become memos.
- `./split-props.md` — first-group-wins claimed set + inverted rest view on both proxy and plain paths.
- `./hydration-ids.md` — pre-order deterministic id grammar (`id + letter-width + digits`).
- `./web-layer-surface.md` — Portal owner-anchored content, Dynamic typeof dispatch, dom-expressions boundary.
- `./babel-preset-config.md` — JSX transform config surface, builtIns escape list, getter-props convention.
- `./observable-bridge.md` — accessor→ES Observable: per-subscribe root+effect, untracked handler, owner-tied disposal.
- `./from-producer-bridge.md` — producer→Accessor: two producer shapes, equals:false push semantics, no subscription sharing.
- `./interop-server-twin-drift.md` — what survives SSR compile-out in the bridges; from() loses initialValue; enableExternalSource stubbed.
- `./hyperscript-adapter.md` — compiler-free h: six-op DI contract + jsx/jsxs/jsxDEV single-alias runtime.
- `./browser-stub-twins.md` — fail-soft browser stubs of renderToString/Async/Stream + empty-shape ssr* helpers.
- `./reconcile-array-diff-internals.md` — how does applyState reuse nodes when keys repeat, reorder, appear, and vanish.
- `./server-web-entry-twin.md` — what must a solid-js/web server entry provide beyond dom-expressions, and what does it deliberately compile Portal down to.
- `./store-unwrap-contract.md` — what does unwrap() guarantee about its input, its output, and itself under SSR.

## Capsule map
- **Kernel: read** — `signal-core.md`: bound readSignal registers Listener once per run (tail check) into parallel arrays; serves tValue under transitions. `runtop-pull-ladder.md`: PENDING reads resolve upstream first via owner-walk + epoch guard; each node runs ≤1× per batch.
- **Kernel: write** — `write-path.md`: comparator gate → value/tValue store → direct observers STALE+queued by purity → markDownstream PENDING recursion; Updates>10e5 throws. `batch-transitions.md`: nested runUpdates joins outermost; transitions park effects and atomically commit tValues on last promise.
- **Kernel: lifecycle** — `ownership-disposal.md`: owned-list tree, newest-first cleanups, pop-and-swap-remove subscription teardown, per-rerun dependency recollection. `effect-tiers.md`: pure-sync/render/user ladder; user effects defer past render and stash during hydration.
- **Async** — `resource-fsm.md`: pr-identity guard makes out-of-order resolutions safe; refreshing keeps old value; errors only throw when idle. `suspense-ladder.md`: increment/decrement counter flips fallback; suspended effects park in store.effects and resume; fallback root reused to kill flicker.
- **Errors** — `error-boundaries.md`: context[ERROR] handler lists walked up owners; batches defer handlers as synthetic Effects. `error-boundary-component.md`: the boundary is a memo running children inside catchError; reset = clear signal.
- **Lists** — `map-array-diff.md`: keyed-by-identity diff (prefix/suffix/backward Map + duplicate chain); each row its own root; index accessors fire on move.
- **Scheduling** — `time-slice-scheduler.md`: MessageChannel loop, 5ms yield / 300ms cap, expiration-order binary insert, lazy cancel, unref for Node.
- **Interop** — `external-source-bridge.md`: onion-composed factories wrap every computation fn over an internal equals:false trigger signal; post-transition re-trigger rescues lost subscriptions.
- **Stores: read** — `store-proxy-traps.md`: lazy tracked property signals created only under a Listener; has-trap tracks membership; methods stay untracked; class getters rebound to proxy.
- **Stores: write** — `store-write-fanout.md`: equality-gated mutation firing HAS→property→truncation/length→SELF; updatePath accepts key/array/filter/range parts with unsafe-key traversal refusal. `reconcile-produce.md`: key-mismatch replaces subtree, else recurse; produce proxies cached in WeakMap.
- **Stores: variants** — `create-mutable.md`: writable traps + one-batch array-method wrappers + full prototype-chain setter rebinding. `store-server-twin.md`: same grammar zero signals — pollution guards survive compile-out.
- **Control flow** — `show-switch-flow.md`: `!a===!b` equality memos; callback children get throwing narrowed accessors; Switch chains Match priority in one memo.
- **Props** — `merge-props.md`, `split-props.md`: proxy pair implementing defaults layering and group destructuring with identical semantics on plain objects and stores.
- **SSR** — `ssr-shadow-kernel.md`: minimal deletion list preserving owners/context/errors. `ssr-streaming.md`: template-marker fragments + resource data registry + serialize-on-error. `hydration-ids.md`: deterministic pre-order id allocation. `lazy-component.md`: retry-after-reject promise cache shared by all three modes.
- **Compiler/host surface** — `babel-preset-config.md`: external jsx-dom-expressions configured here; builtIns must not be component-wrapped; getter-props is the laziness contract. `web-layer-surface.md`: Portal/Dynamic sit on dom-expressions; marker-node anchoring; `_$host` delegation link.
- **Interop & adaptation plane** — `observable-bridge.md` + `from-producer-bridge.md`: accessor↔Observable/producer bridges built only from kernel primitives; `interop-server-twin-drift.md`: the SSR twin keeps observable byte-identical but narrows from() and stubs enableExternalSource; `hyperscript-adapter.md`: six-op DI defines the host for compiler-free templates; `browser-stub-twins.md`: signature-parity fail-soft stubs let SSR render APIs ride in client bundles.
- **Reconcile array-diff internals** — `reconcile-array-diff-internals`: how does applyState reuse nodes when keys repeat, reorder, appear, and vanish.
- **Server web-entry twin** — `server-web-entry-twin`: what must a solid-js/web server entry provide beyond dom-expressions, and what does it deliberately compile Portal down to.
- **Store unwrap contract** — `store-unwrap-contract`: what does unwrap() guarantee about its input, its output, and itself under SSR.
## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
SolidJS solid (MIT, `main@f47845f9cc16ecbb316aa6560c7161f45af9a3d8`, v1.9.x line); Codebase Memory project `solid` (full index: 2,353 nodes / 6,174 edges, head == base_sha, generation 2026-08-25T20:12:15Z). Passes 1 (26 capsules) were authored against the same pin via the since-retired `ext-solid` graph; pass 2 re-indexed fresh as `solid`, re-verified HEAD == pin by git, and refreshed live retrieval targets. All cited source/test paths report `no_recorded_issue` + `metadata_match` + `generation_matches=true` on `check_index_coverage`. 5 parse_partial files are peripheral examples/bench code — none cited.

## Full view (memory graph)
Revalidate `solid` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record graph root `/mnt/hdd/utopia/inspo/solid`, branch main @ `f47845f9cc16ecbb316aa6560c7161f45af9a3d8` (head==base_sha, fresh), full mode, ready. Graph caveats: BM25 search_graph matches Function-class tokens strongly but bench/library twins dominate some queries — filter results to `packages/solid/src|store/src|test`; the token-poor `packages/solid/h/` shim needs a `name_pattern` fallback query. Direct vitest runner BLOCKED in this clone (no node_modules; node v26 present): probes were verified byte-exact against source/test files on disk instead; test line references pin behavior claims honestly.

## Boundaries
Adopt the kernel contracts wholesale: mark-vs-run separation, pull-based topological execution, ownership/disposal bookkeeping, resource promise-identity guard, store trap/fan-out protocols, keyed reconcile diff, SSR deletion list, hydration-id determinism. Adapt module-global `Listener/Owner/Updates/Effects` into host-appropriate contexts, MessageChannel to your scheduler, symbol names, and error text. Omit dom-expressions internals and babel-plugin-jsx-dom-expressions themselves (external packages — separate repos), solid-element custom-element wrapper, universal/html build targets, and bench/prototypes unless a target needs them.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`babel-preset-config.md`](./babel-preset-config.md)
- [`batch-transitions.md`](./batch-transitions.md)
- [`browser-stub-twins.md`](./browser-stub-twins.md)
- [`create-mutable.md`](./create-mutable.md)
- [`effect-tiers.md`](./effect-tiers.md)
- [`error-boundaries.md`](./error-boundaries.md)
- [`error-boundary-component.md`](./error-boundary-component.md)
- [`external-source-bridge.md`](./external-source-bridge.md)
- [`from-producer-bridge.md`](./from-producer-bridge.md)
- [`hydration-ids.md`](./hydration-ids.md)
- [`hyperscript-adapter.md`](./hyperscript-adapter.md)
- [`interop-server-twin-drift.md`](./interop-server-twin-drift.md)
- [`lazy-component.md`](./lazy-component.md)
- [`map-array-diff.md`](./map-array-diff.md)
- [`merge-props.md`](./merge-props.md)
- [`observable-bridge.md`](./observable-bridge.md)
- [`ownership-disposal.md`](./ownership-disposal.md)
- [`reconcile-array-diff-internals.md`](./reconcile-array-diff-internals.md)
- [`reconcile-produce.md`](./reconcile-produce.md)
- [`resource-fsm.md`](./resource-fsm.md)
- [`runtop-pull-ladder.md`](./runtop-pull-ladder.md)
- [`server-web-entry-twin.md`](./server-web-entry-twin.md)
- [`show-switch-flow.md`](./show-switch-flow.md)
- [`signal-core.md`](./signal-core.md)
- [`split-props.md`](./split-props.md)
- [`ssr-shadow-kernel.md`](./ssr-shadow-kernel.md)
- [`ssr-streaming.md`](./ssr-streaming.md)
- [`store-proxy-traps.md`](./store-proxy-traps.md)
- [`store-server-twin.md`](./store-server-twin.md)
- [`store-unwrap-contract.md`](./store-unwrap-contract.md)
- [`store-write-fanout.md`](./store-write-fanout.md)
- [`suspense-ladder.md`](./suspense-ladder.md)
- [`time-slice-scheduler.md`](./time-slice-scheduler.md)
- [`web-layer-surface.md`](./web-layer-surface.md)
- [`write-path.md`](./write-path.md)
