<!-- capsule-v2 -->
# Cursor & stylesheet micro-plugins — body-wide cursor lock via the injector contract

**Source:** dnd-kit MIT `main@6fb57833026e06bb3925eef78316ba56d59749c8`; Codebase Memory `ext-ui-dnd-kit`. **Question:** How is a global grabbing cursor enforced during drags and cleaned up without leaking styles?

## Cursor plugin
**Path/Symbol:** `packages/dom/src/core/plugins/cursor/Cursor.ts:14-39`.
**Signature:** `new Cursor(manager, {cursor? = 'grabbing'})`; resolves the StyleInjector instance from `manager.registry.plugins.get(StyleInjector)` and registers one rule: `` `* { cursor: ${cursor} !important; }` ``.
**Data Shape:** none beyond the injector's refcount registry — Cursor holds no state of its own.

### Decisive source
```ts
const styleInjector = manager.registry.plugins.get(StyleInjector as any) as StyleInjector | undefined;
const unregisterStyles = styleInjector?.register(
  `* { cursor: ${cursor} !important; }`
);

if (unregisterStyles) {
  const originalDestroy = this.destroy.bind(this);
  this.destroy = () => {
    unregisterStyles();
    originalDestroy();          // compose rather than override base teardown
  };
}
```

**Flow:** constructor → optional injector lookup (absent ⇒ degrade silently, no cursor styling) → register rule (injector fans it to every active root per its own effect) → destroy composes unregister + super teardown. Because injection is drag-scoped inside StyleInjector (`roots` is empty when idle), the cursor rule only lands in documents/shadow roots involved in an active drag.
**Invariant:** destroy composition must call the ORIGINAL bound destroy exactly once (re-binding `this.destroy` twice would drop cleanup); the `?.` on styleInjector makes Cursor safe in hosts that never install the injector — porting it as a hard dependency breaks minimal setups.
**Probe:** plugin lifecycle matrix pinned by `plugin-registry.test.ts` (destroy-once semantics); rule text verified by direct source read at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-dnd-kit", query: "Cursor", name_pattern: "^Cursor$", limit: 10 });
```

## Verdict
Adopt the optional-dependency + composed-destroy pattern for any plugin piggybacking shared resources; adapt the selector/cursor default to your design tokens; omit nothing — this is the reference 30-line plugin shape.
