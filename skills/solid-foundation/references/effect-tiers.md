<!-- capsule-v2 -->
# Solid effect tiers — why do createComputed/createRenderEffect run synchronously while createEffect defers, and what does `user` buy?

**Source:** SolidJS solid MIT `main@f47845f9cc16ecbb316aa6560c7161f45af9a3d8`; Codebase Memory `solid` (pass-3 refresh from retired `ext-solid` @ identical pin). **Question:** What exactly distinguishes the four creation primitives at runtime?

## Effect tier matrix
**Path/Symbol:** `packages/solid/src/reactive/signal.ts:createComputed` (:298-306), `createRenderEffect` (:323-337), `createEffect` (:360-371), `createMemo` (:442-465).
**Signature:** all share `(fn: EffectFunction<Init|Next, Next>, value?: Init, options?: EffectOptions)`; `createEffect` options add `{ render?: boolean }`.
**Data Shape:** `pure` flag (memo/computed = true; effects = false) chooses Updates vs Effects queue; `user` flag routes user effects behind render effects in the drain; initial `state` argument to createComputation is `STALE` for computed/render/effect but `0` for memo and reaction.

### Decisive source
```ts
// createComputed — runs NOW (synchronously), pure:
const c = createComputation(fn, value!, true, STALE, ...);
if (Scheduler && Transition && Transition.running) Updates!.push(c);
else updateComputation(c);

// createEffect — deferred, impure, user-flagged:
runEffects = runUserEffects;
const c = createComputation(fn, value!, false, STALE, ...),
    s = SuspenseContext && useContext(SuspenseContext);
if (s) c.suspense = s;
if (!options || !options.render) c.user = true;
Effects ? Effects.push(c) : updateComputation(c);
```

**Flow:** createComputed → immediate `updateComputation` (runs fn inline under Listener) → createRenderEffect → same but queued as non-pure so it runs after all pure updates in the current batch → createEffect → pushed to `Effects`; when drained, `runUserEffects` (:1646-1668) runs ALL non-user computations first, then user ones — and during hydration stashes pending user effects in `sharedConfig.effects` keyed on `sharedConfig.count/done` for client replay.
**Invariant:** The tier ladder is a contract, not a hint: writes inside a computed are visible to later computeds in the same batch ("Test cross setting in a effect update", signals.spec :374-392); user effects never observe half-applied render state. `createMemo` differs from computed by RETURNING an accessor bound to itself and starting clean (`state=0`) — it evaluates lazily on first read. Forgetting the `user` flag makes component effects fire before render effects complete and breaks hydration ordering.
**Probe:** `grep -c 'c.user = true' packages/solid/src/reactive/signal.ts` → matches createReaction + createEffect sites; tier split pinned by `test/signals.spec.ts` "Groups updates" family (:308-392) which relies on effects deferring past synchronous memos.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "solid", query: "createComputed createRenderEffect createEffect user pure", limit: 10 });
```

## Verdict
Adopt the three-tier semantics (sync-pure / render / user-effect) + hydration effect-stash. Adapt tier names to host vocabulary. Omit Suspense attachment (`c.suspense = s`) until Suspense is ported.
