<!-- capsule-v2 -->
# Solid lazy — how does one component factory serve sync client, async hydration, and SSR block modes?

**Source:** SolidJS solid MIT `main@f47845f`; Codebase Memory `ext-solid`. **Question:** What does the load promise cache do on rejection, and how do the three render modes differ?

## component.ts lazy (client) vs server/rendering.ts lazy (server)
**Path/Symbol:** `packages/solid/src/render/component.ts:lazy` (:360-427); server twin `packages/solid/src/server/rendering.ts:lazy` (:556-608).
**Signature:** `lazy<T extends Component<any>>(fn: () => Promise<{ default: T }>): T & { preload(): Promise<{ default: T }> }`.
**Data Shape:** client closure `comp?: (() => T) | undefined`, `p?: Promise` (nulled on FAILURE so a later call retries); hydration path counts pending lazies in `sharedConfig.count` and stashes resolved user effects for replay.

### Decisive source
```ts
const load = () => {
    if (!p) {
      const cur = (p = fn());
      cur.then(
        mod => { comp = () => mod.default; },
        () => { if (p === cur) p = undefined; }   // ← rejection un-caches, retry allowed
      );
    }
    return p;
};
```

**Flow:** first render triggers `load()`; client non-hydrating path wraps resolution in `createResource(() => load().then(mod => mod.default))` so Suspense can catch it, memoizing the component choice with `createMemo`, rendering `""` until ready. Hydration path increments `sharedConfig.count`, restores hydrate context around the eventual `set(...)`, and decrements — enabling `runUserEffects`'s deferred-effects replay. Server path returns `""` immediately and calls `sharedConfig.context.block(p)` (see ssr-streaming capsule).
**Invariant:** The `p === cur` identity check means only the FAILED attempt is discarded while a newer retry's promise stays cached. `comp` is captured per-render (`onCleanup(() => (comp = undefined))`) so disposal re-arms loading. Dev mode tags resolved components with `$DEVCOMP`.
**Probe:** `grep -c 'if (p === cur) p = undefined;' packages/solid/src/render/component.ts` → `1`. Behavior pinned by test/server/lazy.spec.ts (:38-94).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-solid", query: "lazy preload comp sharedConfig.count", limit: 10 });
```

## Verdict
Adopt failure-uncaching + per-mode render strategy. Adapt to host code-splitting primitives. Omit dev tagging freely.
