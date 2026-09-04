<!-- capsule-v2 -->
# Solid SSR store twin — why does the server copy of the store have no signals at all, and what does `force` change?

**Source:** SolidJS solid MIT `main@f47845f`; Codebase Memory `ext-solid`. **Question:** What is the minimal write-side contract that must survive when reactivity is compiled out?

## store/src/server.ts: signal-free setProperty/updatePath
**Path/Symbol:** `packages/solid/store/src/server.ts:setProperty` (:32-38), `unwrap` (:28-30), `updatePath` (:70-116), `isWrappable` (:20-26).
**Signature:** `setProperty(state: any, property: PropertyKey, value: any, force?: boolean)` — note 4th param renamed `deleting → force` with INVERTED meaning.
**Data Shape:** `$RAW` only (no $NODE/$HAS/$SELF); `unwrap` is identity; `isWrappable` drops the $PROXY fast path and class-instance tolerance.

### Decisive source
```ts
export function unwrap<T>(item: T): T {
  return item;
}
export function setProperty(state: any, property: PropertyKey, value: any, force?: boolean) {
  if (property === "__proto__") return;
  if (!force && state[property] === value) return;
  if (value === undefined) {
    delete state[property];
  } else state[property] = value;
}
```

**Flow:** identical updatePath grammar and unsafe-key guards as the client, but every notification branch is deleted — writes are plain mutations guarded by equality. The `force` flag exists because server reconcile/produce callers (`mergeStoreNode(..., force)`) need to overwrite equal values to keep serialized output deterministic across renders.
**Invariant:** The prototype-pollution guard survives in FULL on the server (updatePath :78-79 refuses unsafe traversal even with zero reactivity) — security invariants are compile-out-independent. Any porter who deletes the reactive layer must keep: equality short-circuit semantics, undefined-means-delete, and the unsafe-key refusals.
**Probe:** `grep -c 'export function unwrap<T>(item: T): T {' packages/solid/store/src/server.ts` → `1`; `grep -c 'if (!force && state[property] === value) return;' packages/solid/store/src/server.ts` → `1`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-solid", query: "server setProperty updatePath unwrap", limit: 10 });
```

## Verdict
Adopt as the reference for what a "dead-code-eliminated" build of your state layer must preserve. Adapt freely — this file IS the adaptation guide. Omit nothing if you ship SSR.
