<!-- capsule-v2 -->
# Solid hydration ids — how does the sharedConfig counter generate deterministic hydration keys across server and client?

**Source:** SolidJS solid MIT `main@f47845f`; Codebase Memory `ext-solid`. **Question:** What is the id grammar and who increments the counter?

## render/hydration.ts: getContextId / getNextContextId / nextHydrateContext
**Path/Symbol:** `packages/solid/src/render/hydration.ts` (whole file :1-48).
**Signature:** `sharedConfig.getContextId(): string` (peek), `getNextContextId(): string` (increment), `nextHydrateContext(): HydrationContext`.
**Data Shape:** `HydrationContext { id: string; count: number }`; `SharedConfig` additionally carries `registry: Map<string, Element>`, `effects`, `done`, `load/has/gather`, `getContextId/getNextContextId`.

### Decisive source
```ts
getContextId() { return getContextId(this.context!.count); },
getNextContextId() { return getContextId(this.context!.count++); }
...
function getContextId(count: number) {
  const num = String(count),
    len = num.length - 1;
  return sharedConfig.context!.id + (len ? String.fromCharCode(96 + len) : "") + num;
}
export function nextHydrateContext(): HydrationContext | undefined {
  return { ...sharedConfig.context, id: sharedConfig.getNextContextId(), count: 0 };
}
```

**Flow:** each component boundary (createComponent under hydration) calls `setHydrateContext(nextHydrateContext())` on entry and restores the parent context after — a depth-first pre-order walk where every node consumes exactly one id. Id grammar: parent-id + letter-prefix for digit-count ("a"=2 digits, "b"=3, …) + digits — e.g. root children are `0`,`1`,…; grandchildren of `0` are `0a0`, `0a1`. Resources/lazy/Suspense reserve ids via `getNextContextId()` at CREATION time so registration order matches traversal order.
**Invariant:** Determinism is the whole contract: server allocation order must equal client traversal order or registry lookups miss. That's why SSR fallback branches reset `count: 0` when re-entering with a suffixed id ("0F"), and why `createUniqueId` uses the same allocator during hydration. The client-side `registry` maps ids to real DOM nodes as it walks.
**Probe:** `grep -c 'String.fromCharCode(96 + len)' packages/solid/src/render/hydration.ts` → `1`. Behavior pinned indirectly by test/rendering.spec.ts hydration cases.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-solid", query: "hydration sharedConfig nextHydrateContext getNextContextId", limit: 10 });
```

## Verdict
Adopt pre-order deterministic id allocation with letter-width escaping for any resumable serialization. Adapt grammar freely as long as both sides agree. Omit gather/load until resources-on-server.
