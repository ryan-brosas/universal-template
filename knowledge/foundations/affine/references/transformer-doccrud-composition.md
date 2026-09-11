<!-- capsule-v2 -->
# DocCRUD composition root — how is the Transformer bound to a live workspace, and which middlewares ship by default?

**Source:** AFFiNE MIT `canary@<pin>`; Codebase Memory `ext-affine`. **Question:** What does a production wiring site pass for blobCRUD/docCRUD/middlewares when importing HTML into a collection?

## Production wiring: `importHTMLToDoc`
**Path/Symbol:** `blocksuite/affine/widgets/linked-doc/src/transformers/html.ts:95-125` (`importHTMLToDoc`; export twin `exportDoc` :84-93 uses `doc.getTransformer([docLinkBaseURLMiddleware, titleMiddleware])`).
**Signature:** `new Transformer({ schema, blobCRUD: collection.blobSync, docCRUD: { create, get, delete }, middlewares })`.
**Data Shape:** docCRUD methods close over the Workspace (`collection`) — `create: id => collection.createDoc(id).getStore({ id })`, `get: id => collection.getDoc(id)?.getStore({ id }) ?? null`, `delete: id => collection.removeDoc(id)`.

### Decisive source
```ts
// html.ts:103-115 — the exact production recipe
const job = new Transformer({
  schema,
  blobCRUD: collection.blobSync,
  docCRUD: {
    create: (id: string) => collection.createDoc(id).getStore({ id }),
    get: (id: string) => collection.getDoc(id)?.getStore({ id }) ?? null,
    delete: (id: string) => collection.removeDoc(id),
  },
  middlewares: [
    defaultImageProxyMiddleware,
    fileNameMiddleware(fileName),
    docLinkBaseURLMiddleware(collection.id),
  ],
});
const htmlAdapter = new HtmlAdapter(job, provider);
const page = await htmlAdapter.toDoc({ file: html, assets: job.assetsManager });
```

**Flow:** transformer construction is cheap and per-operation — every import/export call builds a fresh job with exactly the middlewares that operation needs; nothing global caches it. The adapter receives the same job so snapshot conversion and format conversion share one AssetsManager. Export path swaps middleware set (title + doc-link base URL) but reuses `getTransformer` on the Store.
**Invariant:** (1) `get` returning `null` (not throw) is the contract replaceIdMiddleware's linked-doc check depends on to decide "doc exists elsewhere". (2) Middleware selection is per-direction: import needs image-proxy + filename; export needs title registry + base URL — porters copying one set to both directions produce broken links or lost titles. (3) Same `new Transformer(...)` pattern repeats in zip/notion-html/bear transformers of this widget — the composition shape is stable across formats.
**Probe:** `grep -rn 'new Transformer(' blocksuite/affine/widgets/linked-doc/src/transformers/ | wc -l` → `5` (html ×2, bear, notion-html, zip).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-affine", query: "importHTMLToDoc new Transformer collection blobSync docCRUD", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt per-operation transformer construction with direction-specific middleware sets. Adapt CRUD adapters to your workspace facade. Omit the null-returning get and reference-preserving imports start duplicating unrelated docs.
