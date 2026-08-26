<!-- capsule-v2 -->
# Computed pull model + globalVersion — when does a computed re-evaluate, propagate, and stay cached?

**Source:** vue-core MIT `main@e2bede96`; Codebase Memory project `ext-vue-core`. **Question:** What is the exact dirty-check ladder a porter must implement so chained computeds re-compute the minimum and never serve stale values?

## ComputedRefImpl as Subscriber with version fast paths
**Path/Symbol:** `packages/reactivity/src/computed.ts:ComputedRefImpl` (:47-154), `get value` (:131-145), `notify` (:117-129); `packages/reactivity/src/effect.ts:refreshComputed` (:376-430), `isDirty` (:353-370); `packages/reactivity/src/dep.ts:globalVersion` (:19).
**Signature:** `class ComputedRefImpl<T> implements Subscriber { dep: Dep; globalVersion; _value; fn: (oldValue?) => T }`, `get value(): T`.
**Data Shape:** computed holds its OWN `dep` (what others subscribe to) while acting as a Subscriber to source deps (its `deps` Link list). `flags = DIRTY` initially; `globalVersion` initialized to `globalVersion - 1` forces first evaluation. Getter receives previous value as optional arg.

### Decisive source
```ts
get value(): T {
  const link = this.dep.track()      // subscribe MY dep to the outer consumer
  refreshComputed(this)
  if (link) link.version = this.dep.version   // sync AFTER evaluation
  return this._value
}
// refreshComputed ladder:
// 1) TRACKING && !DIRTY -> clean, skip
// 2) globalVersion === current -> nothing changed anywhere since last refresh, skip
// 3) EVALUATED && (no deps || !isDirty(computed)) -> skip
// 4) else evaluate under activeSub=this; bump dep.version ONLY on real change:
if (dep.version === 0 || hasChanged(value, computed._value)) {
  computed._value = value; dep.version++
}
```

**Flow:** mutation → source `Dep.trigger` bumps own+globalVersion and notifies subs → computed's `notify()` sets DIRTY and returns true so `Dep.notify` cascades ONE hop up (`(link.sub).dep.notify()` — inlined to cut stack depth, dep.ts :193-200) → on next read, `value` tracks then refreshComputed walks the ladder; unchanged results leave `dep.version` untouched so downstream effects never fire.
**Invariant:** Version bumps happen only on actual change — that is what makes "chained computed avoid re-compute" hold; error path still bumps `dep.version++` before rethrowing (:421-423) so waiters retry instead of caching the throw; SSR computeds skip the dirty ladder entirely and lean on globalVersion (#12337: no-deps evaluated computed never re-runs).
**Probe:** `packages/reactivity/__tests__/computed.spec.ts:650` (`chained computed avoid re-compute` — src mutated 3× but c1 %2 stable ⇒ c2Spy and effectSpy each called exactly once).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-vue-core", query: "refreshComputed globalVersion", limit: 10 });
```

## Verdict
Adopt the whole ladder (flags → globalVersion → isDirty) in order — reordering breaks either staleness or perf. Adapt getter's oldValue parameter if your host lacks it. Omit writable-computed setter warning path if you have no dev warnings.
