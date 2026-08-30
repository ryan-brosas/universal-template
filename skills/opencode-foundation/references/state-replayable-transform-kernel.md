<!-- capsule-v2 -->
# State replayable-transform kernel — how do five domain stores share one substrate where "config beats built-ins" is just replay order and a closed scope removes a contribution?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** Several domain registries (agents, commands, skills, catalog, integrations) are written by both built-ins and user config, must support "later registration wins", must forget a contributor when its scope closes, and must never expose half-built state under interruption. What kernel makes all of that true without per-domain locking code?

## One kernel: ordered replayable transforms over a rebuilt-from-scratch state
**Path/Symbol:** `packages/core/src/state.ts` (`State.create` :61-128, `materialize` :78-84, `commit` :66-70, `batch` :33-42, `CurrentBatch` :29-31, `transform` :88-122).
**Signature:** `State.create<State, DraftApi>({initial, draft, finalize?}) → {get, transform, reload}`; `transform(update: (draft: DraftApi) => void | Effect<void>) → Effect<{dispose}, never, Scope.Scope>`; `State.batch(effect) → Effect`.
**Data Shape:** kernel holds `state` (the committed value) plus `transforms: {run}[]` (ordered callbacks). Domains supply `initial()` (fresh empty Data), `draft(state)` (the write API over that Data), optional `finalize(draft)` (runs after all transforms, before commit).

### Decisive source
```ts
// state.ts:78-84 — every rebuild starts EMPTY and replays ALL transforms in order
const materialize = Effect.fnUntraced(function* () {
  const next = options.initial()
  const api = options.draft(next)
  for (const transform of transforms) yield* apply(transform.run, api).pipe(Effect.withSpan("State.reload.update"))
  yield* commit(next)
})
// state.ts:66-70 — finalize runs BEFORE the swap, so an interrupted rebuild never publishes
const commit = Effect.fn("State.commit")(function* (next: State) {
  const api = options.draft(next)
  if (options.finalize) yield* options.finalize(api)
  state = next
})
```

**Flow:** `transform(update)` (inside `Effect.uninterruptible`) appends `{run: update}` under a semaphore, registers `dispose` as a Scope finalizer, then reloads — either immediately or by adding `reload` to the ambient `CurrentBatch` set. `dispose` (also uninterruptible, semaphore-guarded, `active` latch makes it once-only) removes the transform and re-materializes (batched if inside `State.batch`). `materialize` builds a FRESH state from `initial()`, wraps it in the domain draft, runs every transform in registration order against the SAME draft, runs `finalize`, then swaps. `State.batch` provides a `Set<Reload>` for its dynamic extent so N transforms across M stores cost ONE rebuild each, run after the batch effect completes.
**Invariant:** a transform is a declarative CONTRIBUTION replayed on every rebuild, never a one-time mutation — "later registration wins" and "config beats built-ins" are literally replay order over a fresh draft; readers always see the last fully-committed state (finalize-before-swap + uninterruptible transform/dispose + one semaphore); closing a contributor's scope deterministically removes exactly its transforms and rebuilds without them; dispose is idempotent (second dispose is a no-op, test-pinned).
**Probe:** `packages/core/test/state.test.ts` (115L, 4 `it.effect`): "commits a transform atomically when its updater is interrupted" blocks finalize, interrupts the transform fiber, asserts the OLD state still visible AND scope-close rebuild yields empty; "runs effectful transforms during every reload" pins effectful transforms re-reading captured values on reload; "disposes a transform once and rebuilds remaining state" pins idempotent dispose; "batches automatic rebuilds" pins finalized===0 inside the batch and ===2 after, across two independent stores. Source pin:
```bash
grep -c 'Effect.uninterruptible' packages/core/src/state.ts   # expect 2
grep -c 'semaphore.withPermit' packages/core/src/state.ts     # expect 3
grep -c 'CurrentBatch' packages/core/src/state.ts             # expect 5
grep -c 'it.effect' packages/core/test/state.test.ts          # expect 4
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "State create transform materialize reload batch CurrentBatch scope finalizer semaphore commit finalize", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the replayable-transform kernel wholesale: fresh-rebuild-per-change, ordered replay as the override mechanism, scope-attached dispose, finalize-before-commit atomicity, and cross-store batching via an ambient reload set. Adapt the Effect specifics (Context.Reference for the batch, Semaphore, Scope finalizers) to your host's structured-concurrency equivalents; omit the Effect span instrumentation. Coverage caveat: Codebase Memory MCP not connected this session — Retrieve marked for re-execution on graph reconnect; bun runner blocked at this checkout (zero node_modules), probes are byte-exact greps.
