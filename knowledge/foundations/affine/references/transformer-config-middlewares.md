<!-- capsule-v2 -->
# titleMiddleware / fileNameMiddleware / filePathMiddleware — how do converter configs flow without constructor plumbing?

**Source:** AFFiNE MIT `canary@<pin>`; Codebase Memory `ext-affine`. **Question:** How are export titles, import filenames, and file paths injected into adapters that run later?

## Three one-purpose config middlewares
**Path/Symbol:** `blocksuite/affine/shared/src/adapters/middlewares/title.ts:1-15`; `file-name.ts:1-27`; `file-path.ts:1-14` (`FULL_FILE_PATH_KEY = 'fullFilePath'`).
**Signature:** `titleMiddleware(metas: DocMeta[])`, `fileNameMiddleware(fileName?: string)`, `filePathMiddleware(filePath: string)` — all `TransformerMiddleware`.
**Data Shape:** `adapterConfigs: Map<string, unknown>` (job-scoped, shared with every adapter via `get configs()`).

### Decisive source
```ts
// title.ts:6-11 — re-publishes the WHOLE registry on every beforeExport tick
export const titleMiddleware =
  (metas: DocMeta[]): TransformerMiddleware =>
  ({ slots, adapterConfigs }) => {
    const beforeExportSubscription = slots.beforeExport.subscribe(() => {
      for (const meta of metas) {
        adapterConfigs.set('title:' + meta.id, meta.title);
      }
    });
    return () => { beforeExportSubscription.unsubscribe(); };
  };

// file-name.ts — mutates the SNAPSHOT, not a config key
payload.snapshot.meta.title = fileName;
payload.snapshot.blocks.props.title = {
  '$blocksuite:internal:text$': true,
  delta: [{ insert: fileName }],
};
```

**Flow:** export side: `beforeExport` fires at the start of `docToSnapshot`/`sliceToSnapshot`/`_blockToSnapshot`, so title entries exist before any adapter serializes text referencing another doc's title. Import side: `fileNameMiddleware` rewrites BOTH the doc meta title and the root block's Text prop (via the tagged-delta envelope) during the page-level beforeImport event — i.e., naming happens before any block-level id or content processing. filePath writes a static key once at middleware init.
**Invariant:** (1) The two name channels are DIFFERENT mechanisms: title→config map (read by adapters), fileName→snapshot mutation (read by transformer itself); porters who unify them break either cross-doc titles or import naming. (2) The delta envelope in fileName must match TEXT_UNIQ_IDENTIFIER exactly or the revived root title is a plain object, not Text.
**Probe:** `grep -n "adapterConfigs.set" blocksuite/affine/shared/src/adapters/middlewares/title.ts | cut -d: -f1` → `9`. And `grep -c "slots.beforeImport.subscribe\|beforeExportSubscription = slots.beforeExport.subscribe" blocksuite/affine/shared/src/adapters/middlewares/file-name.ts title.ts` → per-file counts `1` and `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-affine", query: "titleMiddleware adapterConfigs fileNameMiddleware meta title", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt config-map + snapshot-mutation as the two sanctioned injection channels; keep them distinct. Adapt key naming to your namespace. Omit the whole-registry refresh per event and exports after mid-run meta edits carry stale titles.
