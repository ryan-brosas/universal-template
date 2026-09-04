<!-- capsule-v2 -->
# trigger fan-out grammar — which extra deps must a SET/ADD/DELETE/length write wake beyond the key itself?

**Source:** vue-core MIT `main@e2bede96`; Codebase Memory project `ext-vue-core`. **Question:** What is the exact dep-expansion table on mutation so iteration and length watchers stay consistent?

## Key → implicit keys expansion before notify
**Path/Symbol:** `packages/reactivity/src/dep.ts:trigger` (:294-389), `ITERATE_KEY/MAP_KEY_ITERATE_KEY/ARRAY_ITERATE_KEY` (:242-250), `getDepFromReactive` (:391-397).
**Signature:** `trigger(target, type: TriggerOpTypes, key?, newValue?, oldValue?, oldTarget?): void`.
**Data Shape:** TriggerOpTypes {SET, ADD, DELETE, CLEAR}; special depsMap keys are the three iterate Symbols plus `'length'`; `depsMap: Map<key, Dep>` inside module WeakMap `targetMap`.

### Decisive source
```ts
if (targetIsArray && key === 'length') {
  const newLength = Number(newValue)
  depsMap.forEach((dep, key) => {
    if (key === 'length' || key === ARRAY_ITERATE_KEY || (!isSymbol(key) && key >= newLength)) run(dep)
  })                                   // shrinking length wakes every index >= newLength
} else {
  if (key !== void 0 || depsMap.has(void 0)) run(depsMap.get(key))
  if (isArrayIndex) run(depsMap.get(ARRAY_ITERATE_KEY))       // any index write wakes array iteration
  switch (type) {
    case ADD: if (!targetIsArray) { run(depsMap.get(ITERATE_KEY)); if (isMap(target)) run(depsMap.get(MAP_KEY_ITERATE_KEY)) }
              else if (isArrayIndex) run(depsMap.get('length')); break
    case DELETE: /* ITERATE (+MAP_KEY_ITERATE for maps) */ break
    case SET: if (isMap(target)) run(depsMap.get(ITERATE_KEY)); break   // map.set counts as size-affecting
  }
}
```

**Flow:** untracked target ⇒ only `globalVersion++` then return (:302-307 — computeds still invalidate globally even with zero subscribers) → CLEAR wakes EVERY dep of the target → otherwise key dep + the expansion table above; each `run` wraps Dep.trigger which bumps version+globalVersion and notifies under start/endBatch.
**Invariant:** Object ADD must wake ITERATE_KEY (`for...in`) AND, for arrays, the `length` dep; plain object SET never wakes ITERATE (no shape change); Map SET wakes ITERATE because map iteration yields entries. Missing any arm produces stale loops/lists after add/delete — the classic porter bug.
**Probe:** `packages/reactivity/__tests__/reactiveArray.spec.ts:175` (`delete on Array should not trigger length dependency`) + `:263` (`track length on for ... in iteration`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-vue-core", query: "track trigger targetMap", limit: 10 });
```

## Verdict
Adopt the expansion table verbatim — it is small and load-bearing. Adapt symbol keys to your own registry names if you rename iterate keys. Omit oldTarget DEV payload unless you ship debugger events.
