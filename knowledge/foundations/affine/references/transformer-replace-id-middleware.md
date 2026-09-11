<!-- capsule-v2 -->
# replaceIdMiddleware — how does pasting duplicate every id while keeping cross-references intact?

**Source:** AFFiNE MIT `canary@<pin>`; Codebase Memory `ext-affine`. **Question:** When importing a slice/doc that may collide with existing ids, what is the full remap order for block ids, database cells, text references, surface elements, and linked docs?

## Six rxjs subscriptions over one shared idMap
**Path/Symbol:** `blocksuite/affine/shared/src/adapters/middlewares/replace-id.ts:20-256` (`replaceIdMiddleware`); before-import page :131-141, block :143-246; after-import fixes :27-127.
**Signature:** `replaceIdMiddleware(idGenerator: () => string): TransformerMiddleware`.
**Data Shape:** `idMap: Map<originalId, newId>` — closure-scoped per middleware instance; grows monotonically, never cleared until disposal.

### Decisive source
```ts
// replace-id.ts:131-141 — page-level rewrite happens BEFORE any block event
const beforeImportPageSubscription = slots.beforeImport
  .pipe(filter(p => p.type === 'page'))
  .subscribe(payload => {
    if (idMap.has(payload.snapshot.meta.id)) {
      payload.snapshot.meta.id = idMap.get(payload.snapshot.meta.id)!;
      return;
    }
    const newId = idGenerator();
    idMap.set(payload.snapshot.meta.id, newId);
    payload.snapshot.meta.id = newId;
  });
```

**Flow:** BEFORE import: (1) page meta id → fresh id via idMap (:131); (2) per-block snapshot ids → fresh ids (:162-170), PLUS two structural fixes on the same event — the `affine:surface` child is moved to END of the page's children (:152-160, surface must load after content) and image/attachment entries in `uploadingAssetsMap` are re-keyed old→new id (:173-180) so in-flight uploads attach to the new block; surface children get PRE-GENERATED ids (:184-192) and connector/group element props are rewritten through idMap with hard `BlockSuiteError 'reference id must exist'` throws on misses (:194-244). AFTER import: database cells re-keyed by idMap (:36-44), paragraph/list deltas get retain-scoped reference.pageId swaps applied as ONE delta (:47-85), surface-ref falls back to generate-new-for-missing-frames / keep-original-for-graphs (:87-105), embed linked/synced doc pageIds regenerate ONLY when `docCRUD.get(original)` is falsy — i.e., links to docs that really exist elsewhere keep pointing there (:108-127).
**Invariant:** (1) Order is load-bearing: all id assignment happens in beforeImport because afterImport consumers (cells/deltas/refs) look up idMap. (2) The map is keyed by ORIGINAL id — a repeated import of the same source slice maps to the SAME new ids (dedupe semantics). (3) Existing-doc detection uses docCRUD, not hasBlock, so whole-doc identity survives copy.
**Probe:** `grep -c 'Subscription = ' …middlewares/replace-id.ts` → `6`. And `grep -n 'reference id must exist' …replace-id.ts | cut -d: -f1` → `205 216 233` (connector source, connector target, group child).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-affine", query: "replaceIdMiddleware id map snapshot surface connector", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the before-assign/after-repair split with a single closure idMap for any copy-paste of referential graphs. Adapt which prop keys count as references. Omit the uploadingAssetsMap re-key and pasting while an image uploads silently detaches it.
