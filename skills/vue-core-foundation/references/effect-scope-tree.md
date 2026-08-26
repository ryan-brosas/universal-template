<!-- capsule-v2 -->
# EffectScope tree — how do effects get disposed together, paused/resumed, and detached safely?

**Source:** vue-core MIT `main@e2bede96`; Codebase Memory project `ext-vue-core`. **Question:** What must a scope port keep so unmounting one scope stops exactly its effects, and async component resumes cannot leak orphans?

## Parent-linked scopes with O(1) swap removal
**Path/Symbol:** `packages/reactivity/src/effectScope.ts:EffectScope` (:6-196), constructor (:47-62), `run` (:106-118), `on/off` (:125-160), `pause` (:68-82), `resume` (:87-104), `stop` (:162-195); helpers `effectScope/getCurrentScope/onScopeDispose` (:207-236).
**Signature:** `class EffectScope { constructor(detached = false); run<T>(fn: () => T): T | undefined; on(): void; off(): void; pause(): void; resume(): void; stop(fromParent?: boolean): void }`.
**Data Shape:** `_active`, `_on` (re-entrant counter for `on()`), `effects[]`, `cleanups[]`, `scopes[]` + per-child `index` for O(1) removal; undetached scopes link `parent` and `prevScope`.

### Decisive source
```ts
// stop: children first (via slice copy — reentrant stop() during cleanup mutates scopes[])
for (let i = 0; i < l; i++) this.scopes[i].stop(true)
// then dereference from parent with swap-pop using the recorded index:
if (!this.detached && this.parent && !fromParent) {
  const last = this.parent.scopes!.pop()
  if (last && last !== this) { this.parent.scopes![this.index!] = last; last.index = this.index! }
}
// off(): LIFO fast path, else unlink mid-chain (async interleaving A restore -> B restore -> A cleanup):
if (activeEffectScope === this) activeEffectScope = this.prevScope
else { let current = activeEffectScope; while (current) { if (current.prevScope === this) { current.prevScope = this.prevScope; break } current = current.prevScope } }
```

**Flow:** `new EffectScope()` under an active parent registers itself (`scopes.push`, index recorded); under a STOPPED parent it self-deactivates (`_active=false`) instead of leaking live → `run()` swaps `activeEffectScope` around fn so nested `effect()`/`computed`/`watch` auto-register → `stop()` stops effects → cleanups → child scopes (copy-iterated) → parent unlink.
**Invariant:** Iteration over `this.effects`/`this.scopes` must use a snapshot copy because user cleanups may stop siblings mid-walk (test :454 `should resume effects when a watcher stops a sibling watcher` guards exactly this); child `stop(true)` skips parent-unlink to avoid double-swap-pop corruption of sibling indices.
**Probe:** `packages/reactivity/__tests__/effectScope.spec.ts:318` (`should pause/resume EffectScope` — paused scope's effect fires zero times while paused, once after resume).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-vue-core", query: "EffectScope pause resume stop", limit: 10 });
```

## Verdict
Adopt the parent/index/swap-pop scheme and the copy-before-callback rule. Adapt `on()/off()` only if your host has no async-context restore need — but keep the mid-chain unlink if anything resumes scopes across awaits. Omit `_warnOnRun` dev warning.
