<!-- capsule-v2 -->
# Transformer middleware slots — what is the exact lifecycle contract middleware authors must honor?

**Source:** AFFiNE MIT `canary@<pin>`; Codebase Memory `ext-affine`. **Question:** Which slot events fire how many times per conversion, and how does middleware register and clean up?

## Four rxjs Subjects + init/cleanup factory
**Path/Symbol:** `blocksuite/framework/store/src/transformer/middleware.ts:101-121` (`TransformerSlots`, options, cleanup type); wiring in `transformer/transformer.ts:70-75` (Subjects) and :368-379 (constructor loop).
**Signature:** `TransformerMiddleware = (options: { assetsManager, slots, docCRUD, adapterConfigs, transformerConfigs }) => void | (() => void)`.
**Data Shape:** Payload unions discriminate on `type`: `'block' | 'slice' | 'page' | 'info'`. Block-level payloads carry position context: `BeforeImportBlockPayload = { snapshot, type:'block', parent?, index? }`; `AfterImportBlockPayload` swaps in the live `model`.

### Decisive source
```ts
// transformer.ts:368-379 — middleware gets EVERYTHING by reference; cleanup is disposable
middlewares.forEach(middleware => {
  const cleanup = middleware({
    slots: this._slots,
    docCRUD: this._docCRUD,
    assetsManager: this._assetsManager,
    adapterConfigs: this._adapterConfigs,
    transformerConfigs: this._transformerConfigs,
  });
  if (cleanup) this._disposables.add(cleanup);
});
```

**Flow (event counts for one `snapshotToDoc`):** beforeImport fires ONCE at `'page'` level (:194) AND once per block via `_triggerBeforeImportEvent` (:612) — so page-level subscribers see the doc BEFORE any block event; afterImport fires per inserted block (:546) then once at `'page'` (:203). Export mirrors it: `'page'` beforeExport once (:102), block-level before/after pairs inside `_blockToSnapshot` (:383/:404), afterExport once with the finished snapshot (:123). Ordering matters: replaceIdMiddleware's page-level id rewrite must run BEFORE block-level events consume ids.
**Invariant:** (1) Middleware receives live Maps (`adapterConfigs`, `transformerConfigs`) — writes there are visible to every later hook resolution, that's how title/filePath settings propagate. (2) Cleanup functions run only via `[Symbol.dispose]()` (:653) — a middleware returning a cleanup MUST also tolerate never being disposed (page-lifetime transformers). (3) Slots are plain Subjects: no replay, no error channel — a throwing subscriber breaks its own pipeline only.
**Probe:** `grep -n 'beforeImport\|afterImport' …transformer/transformer.ts | grep -c 'next('` → `6` (2 page-level + per-block triggers counted by trigger sites); `grep -c 'new Subject<' …middleware-adjacent transformer.ts` → `4` Subjects declared at :71-74. Direct wiring test: constructor loop above is exercised by every spec importing middlewares.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-affine", query: "TransformerSlots beforeImport afterExport payload subject", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the discriminated-union slot bus for converter extensibility. Adapt Subject choice to your reactive stack (Signals/EventEmitter fine) but keep the before×after × import×export symmetry. Omit parent/index context from block payloads and reordering middlewares become impossible.
