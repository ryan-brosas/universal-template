<!-- capsule-v2 -->
# ReactiveEffect lifecycle — how does an effect run, self-clean, recurse safely, and stop idempotently?

**Source:** vue-core MIT `main@e2bede96`; Codebase Memory project `ext-vue-core`. **Question:** What exact flags/stack discipline must a ported effect runner keep so tracking, recursion, pause, and stop behave identically?

## Flag-gated runner around a global activeSub
**Path/Symbol:** `packages/reactivity/src/effect.ts:ReactiveEffect` (:87-228), `run` (:162-192), `stop` (:194-204), `trigger` (:206-214), constructor scope guard (:116-131); `pauseTracking/resetTracking` (:519-544); `cleanupEffect` (:569-582).
**Signature:** `class ReactiveEffect<T> implements Subscriber { deps?; depsTail?; flags; run(): T; stop(): void }`, options `{ scheduler?, allowRecurse?, onStop?, onTrack?, onTrigger? }`.
**Data Shape:** `flags` bitfield — ACTIVE (stopped?), RUNNING, TRACKING, NOTIFIED, DIRTY, ALLOW_RECURSE, PAUSED, EVALUATED. Global mutable `activeSub` + `shouldTrack` form the dynamic tracking context; `trackStack` is the save/restore stack for shouldTrack.

### Decisive source
```ts
run(): T {
  if (!(this.flags & EffectFlags.ACTIVE)) return this.fn()   // stopped: bare fn
  this.flags |= EffectFlags.RUNNING
  cleanupEffect(this)                 // user cleanup BEFORE re-run, with activeSub cleared
  prepareDeps(this)                   // mark all links version=-1
  const prevEffect = activeSub, prevShouldTrack = shouldTrack
  activeSub = this; shouldTrack = true
  try { return this.fn() }
  finally {
    cleanupDeps(this)                 // drop unread links from both lists
    activeSub = prevEffect; shouldTrack = prevShouldTrack
    this.flags &= ~EffectFlags.RUNNING
  }
}
```

**Flow:** construction under an ACTIVE scope registers in `scope.effects` (under a STOPPED scope the flag is stripped pre-emptively so resumed-after-await orphans can never subscribe — :120-129 comment) → run() swaps context, runs fn (reads track via dep.track), restores → trigger() routes by PAUSED → pausedQueueEffects / scheduler / runIfDirty → stop() walks its own links with removeSub, clears deps, runs onStop, clears ACTIVE.
**Invariant:** Recursion guard lives in `notify()` (`RUNNING && !ALLOW_RECURSE ⇒ return`) NOT in run(); cleanup runs BEFORE each re-run and outside the tracking context; stop() is idempotent via the ACTIVE check and a stopped effect's bare-fn path must not track. Losing any of these yields infinite loops on recursive effects or zombie subscriptions after unmount.
**Probe:** `packages/reactivity/__tests__/effect.spec.ts:1286` (`should pause/resume effect` — paused trigger queues in pausedQueueEffects, resume() flushes exactly once).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-vue-core", query: "ReactiveEffect notify batch", limit: 10 });
```

## Verdict
Adopt the flag set and run/finally-restore skeleton verbatim. Adapt scheduler indirection to your flush system (Vue passes job fns from runtime-core). Omit `onTrack/onTrigger` debugger plumbing unless shipping devtools.
