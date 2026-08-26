<!-- capsule-v2 -->
# Transformer error-capture funnel — why does every public conversion return `undefined` instead of throwing?

**Source:** AFFiNE MIT `canary@<pin>`; Codebase Memory `ext-affine`. **Question:** When a porter converts doc/slice/block ⇄ snapshot, which failures throw, which are swallowed, and where must validation run so bad data never enters the store?

## Public API funnel with zod gates at both ends (`Transformer` class)
**Path/Symbol:** `blocksuite/framework/store/src/transformer/transformer.ts:57` (`class Transformer`); gates at :90, :128, :164, :181, :198, :249.
**Signature:** `docToSnapshot(doc: Store): DocSnapshot | undefined`; `snapshotToDoc(snapshot: DocSnapshot): Promise<Store | undefined>`; same `| undefined` shape for `blockToSnapshot`, `sliceToSnapshot`, `snapshotToBlock`, `snapshotToSlice`.
**Data Shape:** Every public method wraps its whole body in try/catch; the catch logs via **two** `console.error` calls (label line + error object) and returns `undefined`. Exactly **8** such label sites exist in the file (grep `console.error(\`Error when transforming` → 8).

### Decisive source
```ts
// transformer.ts:77-98 (block direction; every sibling method repeats the pattern)
blockToSnapshot = (model: DraftModel | BlockModel): BlockSnapshot | undefined => {
  try {
    const draftModel = model instanceof BlockModel ? toDraftModel(model) : model;
    const snapshot = this._blockToSnapshot(draftModel);
    if (!snapshot) return;
    BlockSnapshotSchema.parse(snapshot);   // zod gate AFTER build
    return snapshot;
  } catch (error) {
    console.error(`Error when transforming block to snapshot:`);
    console.error(error);
    return;                                 // NEVER rethrows
  }
};
```

**Flow:** export side: `beforeExport` slot → private build (`_blockToSnapshot`) → `afterExport` slot → `XSnapshotSchema.parse` → return. Import side: `beforeImport` slot → `Schema.parse(snapshot)` FIRST → mutate/create → `afterImport` slot → return.
**Invariant:** (1) Zod parse runs on EVERY public entry in BOTH directions (6 `.parse(` sites total) — import validates BEFORE touching the doc, export validates AFTER building but BEFORE returning. (2) Only two failures escape as real thrown errors *inside* the funnel: missing root (`'Root block not found in doc'`, :111) and missing meta (`'Doc meta not found'`, :479), both `BlockSuiteError(ErrorCode.TransformerError, …)` — and both are still absorbed by the enclosing catch into `undefined`. (3) A porter who replaces `return undefined` with `throw` breaks every caller: adapters (`adapter/base.ts`) treat `undefined` as "skip silently", UI code relies on partial-export success.
**Probe:** `grep -c 'console.error(\`Error when transforming' blocksuite/framework/store/src/transformer/transformer.ts` (anchored at repo root) → `8`. And `grep -n 'Root block not found\|Doc meta not found' …transformer.ts` → lines `111`, `479`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-affine", query: "_insertBlockTree flatten snapshot insert block tree batch", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the swallow-and-log funnel plus zod-at-boundary — it is what lets one corrupt block fail a single conversion without killing a bulk import. Adapt the error label strings to your logger. Omit nothing here; dropping the post-build export parse silently exports invalid snapshots that later imports reject.
