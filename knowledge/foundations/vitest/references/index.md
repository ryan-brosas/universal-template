<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->

# Vitest: Test-Runner Harness Foundation

## Use this for
Build or drive a test-runner harness: serialize overlapping runs and restarts, schedule test files over a bounded worker pool, execute tests with the exact hook/retry/fixture order, stream task updates over IPC, manage snapshot write-vs-match state, select affected tests from a module graph, rewrite ESM so mocks register before imports, drive watch-mode reruns, project/server sharing, and reporter-facing task entities, and port the module-mocking engine itself (resolution queue, external classification, realm primitives, native-hook manual mocks with circular factories, request-time arbitration). Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval. The repo's own e2e/unit suites live under `test/` and are graph-covered in full mode; probes were read on disk at HEAD.

## Load the matching source dump
- `./run-lifecycle.md` — how `Vitest.runFiles` makes overlapping run requests safe and guarantees end-of-run reporting.
- `./restart-coalescing.md` — queued-drain coalescing of chokidar config-change restarts plus the epoch guard for stale watcher callbacks.
- `./spec-grouping.md` — partition specs into groupOrder barriers with correct maxWorkers and no-batch rules for VM pools.
- `./pool-scheduler.md` — bounded recursive scheduler with runner reuse, background termination, and zombie-free cancellation.
- `./state-manager.md` — per-file/per-project state identity, log preservation across recollect, unhandled-error accounting.
- `./reporter-events.md` — worker pack/event stream → ordered reporter callbacks with interrupt>fail>pass end reasons.
- `./test-execution.md` — the per-attempt ladder: repeats × retries × hooks × fixture checkpoints, and failure classification.
- `./around-hooks.md` — aroundEach/aroundAll state machine: split setup/teardown timeouts, single-use callback enforcement.
- `./task-update-throttle.md` — id-coalescing packs + ordered events + trailing-timer throttle that never loses the last update.
- `./mock-hoisting.md` — MagicString AST transform hoisting `vi.mock`/`vi.hoisted` above imports with loud validation errors.
- `./snapshot-state.md` — counter-keyed snapshot reconcile table, retry reset via clearTest, obsolete-key deletion.
- `./related-selection.md` — changed-files → affected-tests reverse-BFS over expand-once import edges.
- `./shutdown-ordering.md` — settle → reverse global teardown → workers before servers → allSettled error folding.
- `./watch-mode-rerun.md` — watcher two-set invalidation (`changedTests` vs `invalidates`) with guarded importer recursion.
- `./watch-debounce-drain.md` — trailing-edge rerun debounce with epoch guard and snapshot-then-clear drain.
- `./interactive-filter-prompt.md` — keypress state machine for the raw-mode terminal filter prompt with wrapped-row ANSI redraw.
- `./project-server-sharing.md` — shared Vite server topology: `_spawnSibling` resource split, (root+name) hash identity, cached close promise.
- `./project-glob-cache.md` — test-file membership cache as authority: mark-on-match, remove-on-delete, exclude-before-include.
- `./reported-task-wrappers.md` — public TestCase/TestSuite/TestModule identity table and strict internal→public state mapping.
- `./fixture-registration-graph.md` — copy-on-write fixture registrations, scope lattice validation, vmThreads worker-scope downgrade.
- `./fixture-use-suspension.md` — `use()` suspension teardown protocol with reverse-order checkpointed cleanup.
- `./fixture-prop-parser.md` — destructuring-string dependency extraction surviving esbuild async lowering, with loud validation errors.
- `./automock-esm-rewrite.md` — execution-free automock ESM surgery incl. deferred `export *` expansion.
- `./browser-mock-queue.md` — browser mock registration queue gated before every dynamic import; unmock/invalidate unwind.
- `./mocker-registry.md` — dual-key (url+id) mock registry: four mock kinds, type dispatch, lazy-cached manual resolve.
- `./mock-object.md` — runtime deep automock/autospy walker with ref-tracked circular resolution and prototype sharing.
- `./export-name-collection.md` — execution-free export enumeration incl. recursive `export *`/CJS re-export expansion.
- `./esm-identifier-walker.md` — scope-aware acorn AST walker (DFS-collect/BFS-emit) for safe import/hoist rewrites.
- `./mock-resolution-queue.md` — pendingIds queue drained at resolution time with consecutive-action grouped ordering.
- `./mock-external-classification.md` — external-vs-file decision ladder plus normalizeModuleId/`mock:` registry-key canonicalization.
- `./mock-realm-primitives.md` — seven captured constructors with vm-context re-capture so mocks stay instanceof-correct across realms.
- `./native-manual-mock-cycle.md` — `{ __factoryPromise }` cycle break for manual mocks that import themselves, incl. the Windows transform-count fallback.
- `./request-mock-arbitration.md` — stale-mock → self-import → automock-freshness → cycle fall-through decision ladder at request time.
- `./clear-files-local-sentinel.md` — never-empty filepath keys via `local: true` placeholder tasks so logs survive invalidation races.
- `./vm-code-cache-rejection-fallback.md` — ESM executor try/catch on `ERR_VM_MODULE_CACHED_DATA_REJECTED`: delete the poisoned entry and compile from source; cachedData is produced strictly before evaluation.
- `./v8-flag-cache-reset.md` — `node:v8` intercepted inside the vm context: `setFlagsFromString` delegates to the host realm then clears the worker-wide code cache in total.
- `./cjs-cross-context-script-cache.md` — module-level `vm.Script` cache shared across fresh vm contexts (static callbacks only); CJS rejection uses the post-construction `cachedDataRejected` flag, store happens after execution.
- `./require-esm-sync-walker.md` — require(esm) worklist walker: scratch-map collect → settled-only cache reuse → link/instantiate → commit-owned-after-success so a failed require never poisons a later import().
- `./fs-module-cache-key.md` — disk transform-cache key = id + content + per-environment digest (NODE_ENV+version+config JSON incl. plugin names with opt-out API) + coverage flag; `import.meta.glob` bails out.
- `./fs-cache-atomic-write.md` — write-then-rename atomic cache files framed as `<code>\n//# vitestCache=<base64 meta>` parsed by lastIndexOf; lockfile-hash mismatch nukes the whole workspace cache.
- `./worker-stdio-early-bind.md` — bound stream writers captured at module load; empty-write drain awaited before every completion signal so thread.terminate() can't drop buffered chunks.
- `./spec-stats-stat-race.md` — advisory file-size census swallows stat races (file deleted mid-flight): absence loses sorting heuristics only, never correctness.
- `./bail-failure-budget.md` — `bail: N` as a cross-process failure budget: worker asks main for the authoritative fail count via RPC and adds its own +1 before cancelling gracefully on two channels.
- `./task-mode-interpretation.md` — post-collection single-pass rewrite of only/skip/todo plus name/location/id/tag filters; unauthorized `.only` fails the TASK, never the run.
- `./each-title-templating.md` — `.each`/`.for` title engine: positional `%` placeholders + `$key` attributes over tuples/scalars/objects/tagged-template tables.
- `./expect-poll-kernel.md` — proxy that turns any matcher into a lazy, await-enforced, deadline-raced polling chain with callsite-correct stacks.
- `./fake-timers-two-axis.md` — FakeTimers state machine: Date-only mocking promotes losslessly to full timer faking; nextTick/queueMicrotask default-denylist.
- `./console-interception.md` — worker-side console buffering with four-rung task attribution, microtask coalescing, and first-write cross-stream ordering.
- `./spyon-descriptor-ownership.md` — spyOn writes an own property on the receiver; restore is owner-aware (delete inherited / redefine new / reassign own).

## Capsule map
- **Orchestration** — `run-lifecycle.md`: single-flight promise loop; pool errors become state errors; `finally` fires coverage + `onTestRunEnd` exactly once. `restart-coalescing.md`: restarts drain one-at-a-time with a trailing re-run; stale callbacks bail on `restartsCount`. `shutdown-ordering.md`: teardown LIFO before servers; pool closes before ports release.
- **Scheduling** — `spec-grouping.md`: groupOrder barriers, sequential/typecheck groups, vm pools never batch. `pool-scheduler.md`: resolver-per-task queue, two-sided runner reuse (`isEqualRunner`), cancel drains queue→actives→shared→exits. `related-selection.md`: reverse-BFS affected set with force-rerun triggers overriding.
- **State & reporting** — `state-manager.md`: filepath-keyed arrays with (project,typecheck,label) identity; AggregateError flattening; VITEST_PENDING special case. `reporter-events.md`: event-name→callback map, synthetic child replay for skipped modules, always-present `stacks`. `task-update-throttle.md`: 100ms trailing-timer flush; events ordered, packs coalesced by id. `clear-files-local-sentinel.md`: invalidation leaves a `local: true` placeholder per filepath so log routing never dangles.
- **In-worker execution** — `test-execution.md`: repeat⊃retry nested loops re-running every hook; fixture checkpoint split; per-stage try/catch failTask. `around-hooks.md`: three-race protocol with separate setup/teardown budgets and `AroundHookMultipleCallsError`.
- **Mocking** — `mock-hoisting.md`: regex prefilter → identifier rebinding → mock/import reorder, with top-level-scope validation errors carrying sourcemapped positions. `automock-esm-rewrite.md`: collect-then-rewrite export surgery producing an execution-free mocked re-export surface; deferred `export *` expansion. `browser-mock-queue.md`: queue+prepare gate so every dynamic import waits for pending mock registrations; type-precedence manual>autospy>redirect>automock. `mocker-registry.md`: dual-key registry where one URL holds exactly one mock of a known type; manual mocks resolve lazily and cache. `mock-object.md`: deep structural walker (automock vs autospy twins) with ref-tracked circular resolution and prototype-chain property collection. `export-name-collection.md`: execution-free lexer enumeration with recursive `export *`/CJS re-export expansion and memoization. `esm-identifier-walker.md`: DFS-collect/BFS-emit scope-aware walker so hoist/import rewrites never corrupt shadowed bindings. `mock-resolution-queue.md`: static pendingIds drained by consecutive-action groups (parallel within, sequential between) at every module resolution. `mock-external-classification.md`: external = unresolvable-or-module-directory; ids normalized (`node:`-strip, `/@fs/`-unwrap, slash-collapse, prefixed-builtin allowlist). `mock-realm-primitives.md`: constructor tuple captured once and atomically re-captured inside vm contexts; single createError factory. `native-manual-mock-cycle.md`: self-importing factories break the cycle via `{ __factoryPromise }` sentinel with a Windows-only transform-count pre-resolve. `request-mock-arbitration.md`: registry is live truth over stamped markers — stale bypass, self-import bypass, freshness re-automock, undefined-means-cycle fall-through.
- **Watch mode** — `watch-mode-rerun.md`: `changedTests`/`invalidates` two-set split; guarded importer recursion; force-rerun-trigger global add; post-restart fallback. `watch-debounce-drain.md`: 100 ms trailing-edge timer, `restartsCount` epoch re-check inside the callback, snapshot-then-clear. `interactive-filter-prompt.md`: raw-mode keypress prompt with finally-restored raw mode and wrapped-row erase math.
- **Project topology** — `project-server-sharing.md`: share-server/own-config sibling split, (root+name) hash, cached idempotent close. `project-glob-cache.md`: cache-as-authority test-file membership with mark-on-match and remove-on-delete.
- **Reporting** — `reported-task-wrappers.md`: WeakMap identity table; result-state-over-mode precedence; suite 4-state vs module +queued vocabulary.
- **Fixtures** — `fixture-registration-graph.md`: copy-on-write override lattice + scope-order validation. `fixture-use-suspension.md`: deferred-`use` teardown with reverse-order checkpointed cleanup. `fixture-prop-parser.md`: destructure-string dep extraction surviving esbuild lowering.
- **Snapshots** — `snapshot-state.md`: `${testName} ${count}` keys, documented write/match table, CI never writes new snapshots, empty-file deletion.
- **Caching & vm compile planes** — `vm-code-cache-rejection-fallback.md`: ESM modules throw `ERR_VM_MODULE_CACHED_DATA_REJECTED` on rejected cachedData (unlike vm.Script's flag); catch → cache delete → recompile from source; store new buffers pre-evaluation. `v8-flag-cache-reset.md`: in-context `node:v8` is prototype-cloned with a delegating `setFlagsFromString` that clears the whole CodeCache (flag changes invalidate every buffer). `cjs-cross-context-script-cache.md`: module-level Script map = compile once per worker, evaluate per context; rejection via post-construction `cachedDataRejected`; store AFTER execution; no invalidation by design. `require-esm-sync-walker.md`: scratch-map worklist, settled-only reuse, per-module TLA rejection, commit owned entries only after whole-graph success. `fs-module-cache-key.md`: sha1(id+content+envHash+coverage) with envHash = digest of NODE_ENV+version+config-JSON; glob bail-out; plugin opt-out API. `fs-cache-atomic-write.md`: tmp-write + rename, trailing base64 meta after last `//# vitestCache=`, lockfile-hash wholesale reset, root-only `_metadata.json`. `worker-stdio-early-bind.md`: bound writes captured at module load, drain awaited before every completion signal. `spec-stats-stat-race.md` (State): advisory size census swallows stat races — absence loses sorting heuristics only.
- **Cross-process policy & authoring surface (pass 6)** — `bail-failure-budget.md` (Orchestration): bail counts against the MAIN process's live fail counter plus the deciding worker's local +1; cancel is graceful and dual-channel. `task-mode-interpretation.md` (Selection): one recursive pass rewrites modes after collection — containsOnly bubbling, filter ladder, cascade skip/todo, fail-the-task allowOnly. `each-title-templating.md` (Authoring): `%#/%$/%f/%%/$key` title grammar with sentinel escaping and tagged-template row folding. `expect-poll-kernel.md` (Authoring): proxy chain-starter + lazy thenable + `{ok,value}` deadline race + pre-captured stacks. `fake-timers-two-axis.md` (Integrations): Date-only ↔ full-faking promotion preserves mocked time; nextTick/queueMicrotask never faked by default. `console-interception.md` (Diagnostics): per-task buffers, first-write timestamps decide stream order, stack-derived attribution fallback. `spyon-descriptor-ownership.md` (@vitest/spy): receiver-only defineProperty with owner-aware restore; SSR getter unwrap; idempotent re-spy.

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf. Each new capsule must carry Path/Symbol, Signature, Data Shape, a labelled decisive source excerpt, Flow, Invariant, a direct-test Probe, and a `search_graph` Retrieve.

## Provenance
Vitest (`vitest-dev/vitest`, MIT, `main@c3ba16b35847d27fb9f01f38cdcb047c77e121f8`, v5 monorepo); Codebase Memory project `vitest` (full index: 16,045 nodes / 52,097 edges, re-indexed in place 2026-08-24 at `c3ba16b3`, head==base). Passes 1–4 mined through `cf9176bf`; pass 5 was a DRIFT RE-ENTRY mining the module-cache/compile plane (#11031, #11029, #11023, #11020); pass 6 (2026-08-25, FAC-109) deep-mined the cross-process policy + runtime authoring surface: bail budget, task-mode interpretation, `.each` templating, expect.poll, FakeTimers axes, console interception, spyOn ownership. Cited source paths report `no_recorded_issue` + `metadata_match` on `check_index_coverage` (best-effort); parse_partial caveats exist only in docs/.d.ts plus `runtime/runner/types.ts` type ranges — none inside cited seams.

## Full view (memory graph)
Revalidate `vitest` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Root `$REFERENCE_ROOT/vitest` (alias `$REFERENCE_ROOT/vitest`; older passes cite the pre-reorg path `inspo/frameworks/vitest`), branch main at `c3ba16b3`, full mode, ready; `jsdom`/`happy-dom` env dirs and asset files are excluded BY DESIGN; 9 parse_partial files are non-blocking.

## Boundaries
Adopt the lifecycle/scheduling/state contracts above — they are host-portable process machinery. Adapt transports (worker_threads/forks/VM/browser), Vite-server specifics (module graphs, environments), reporter vocabularies, and file-layout conventions to the host. Omit the browser runner packages (`packages/browser*`), UI app, coverage providers, benchmark mode, typechecker pool internals, OTel tracing, and Vite plugin plumbing unless a target needs them. Watch-mode and fixture capsules are host-portable; the interactive filter prompt is terminal-specific.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`around-hooks.md`](./around-hooks.md)
- [`automock-esm-rewrite.md`](./automock-esm-rewrite.md)
- [`bail-failure-budget.md`](./bail-failure-budget.md)
- [`browser-mock-queue.md`](./browser-mock-queue.md)
- [`cjs-cross-context-script-cache.md`](./cjs-cross-context-script-cache.md)
- [`clear-files-local-sentinel.md`](./clear-files-local-sentinel.md)
- [`console-interception.md`](./console-interception.md)
- [`each-title-templating.md`](./each-title-templating.md)
- [`esm-identifier-walker.md`](./esm-identifier-walker.md)
- [`expect-poll-kernel.md`](./expect-poll-kernel.md)
- [`export-name-collection.md`](./export-name-collection.md)
- [`fake-timers-two-axis.md`](./fake-timers-two-axis.md)
- [`fixture-prop-parser.md`](./fixture-prop-parser.md)
- [`fixture-registration-graph.md`](./fixture-registration-graph.md)
- [`fixture-use-suspension.md`](./fixture-use-suspension.md)
- [`fs-cache-atomic-write.md`](./fs-cache-atomic-write.md)
- [`fs-module-cache-key.md`](./fs-module-cache-key.md)
- [`interactive-filter-prompt.md`](./interactive-filter-prompt.md)
- [`mock-external-classification.md`](./mock-external-classification.md)
- [`mock-hoisting.md`](./mock-hoisting.md)
- [`mock-object.md`](./mock-object.md)
- [`mock-realm-primitives.md`](./mock-realm-primitives.md)
- [`mock-resolution-queue.md`](./mock-resolution-queue.md)
- [`mocker-registry.md`](./mocker-registry.md)
- [`native-manual-mock-cycle.md`](./native-manual-mock-cycle.md)
- [`pool-scheduler.md`](./pool-scheduler.md)
- [`project-glob-cache.md`](./project-glob-cache.md)
- [`project-server-sharing.md`](./project-server-sharing.md)
- [`related-selection.md`](./related-selection.md)
- [`reported-task-wrappers.md`](./reported-task-wrappers.md)
- [`reporter-events.md`](./reporter-events.md)
- [`request-mock-arbitration.md`](./request-mock-arbitration.md)
- [`require-esm-sync-walker.md`](./require-esm-sync-walker.md)
- [`restart-coalescing.md`](./restart-coalescing.md)
- [`run-lifecycle.md`](./run-lifecycle.md)
- [`shutdown-ordering.md`](./shutdown-ordering.md)
- [`snapshot-state.md`](./snapshot-state.md)
- [`spec-grouping.md`](./spec-grouping.md)
- [`spec-stats-stat-race.md`](./spec-stats-stat-race.md)
- [`spyon-descriptor-ownership.md`](./spyon-descriptor-ownership.md)
- [`state-manager.md`](./state-manager.md)
- [`task-mode-interpretation.md`](./task-mode-interpretation.md)
- [`task-update-throttle.md`](./task-update-throttle.md)
- [`test-execution.md`](./test-execution.md)
- [`v8-flag-cache-reset.md`](./v8-flag-cache-reset.md)
- [`vm-code-cache-rejection-fallback.md`](./vm-code-cache-rejection-fallback.md)
- [`watch-debounce-drain.md`](./watch-debounce-drain.md)
- [`watch-mode-rerun.md`](./watch-mode-rerun.md)
- [`worker-stdio-early-bind.md`](./worker-stdio-early-bind.md)
