<!-- capsule-v2 -->
# MemoryBlobCRUD + mime table — what does a minimal blob backend and asset-name resolver look like?

**Source:** AFFiNE MIT `canary@<pin>`; Codebase Memory `ext-affine`. **Question:** What is the smallest BlobCRUD implementation the transformer accepts, and how are export filenames derived when blobs have no name?

## In-memory CRUD with sha-keyed set + 38-entry MIME→extension map
**Path/Symbol:** `blocksuite/framework/store/src/adapter/assets.ts:7-43` (`MemoryBlobCRUD`, marked "@internal just for test"), :45-129 (`mimeExtMap`), :131-141 (`getExt`), :143-159 (`getAssetName`).
**Signature:** `set(value: Blob): Promise<string>` (sha-keyed overload) / `set(key: string, value: Blob): Promise<string>`; `getAssetName(assets: Map<string, Blob>, blobId: string): string`.
**Data Shape:** `BlobCRUD` interface (transformer/type.ts:63-68) = `{ get, set, delete, list }`; `DocCRUD` (:70-74) = `{ create, get, delete }`.

### Decisive source
```ts
// adapter/assets.ts:26-31 — content-addressed default key
async set(valueOrKey: string | Blob, _value?: Blob) {
  const key = typeof valueOrKey === 'string'
    ? valueOrKey
    : await sha(await valueOrKey.arrayBuffer());
  ...
}
// adapter/assets.ts:135-141 — extension fallback ladder: '' → 'blob', table hit, else last path segment
const getExt = (type: string) => {
  if (type === '') return 'blob';
  const ext = mimeExtMap.get(type);
  if (ext) return ext;
  const guessExt = type.split('/');
  return guessExt.at(-1) ?? 'blob';
};
```

**Flow:** `getAssetName`: File with name? → keep it verbatim (`image.jpg` with png type stays `image.jpg` — test-pinned "respect the original name") → name WITHOUT dot gets `.${getExt(type)}` appended → no name at all falls back to `${blobId}.${ext}`. The mime table is exactly **38** `'application/…'` rows (plus audio/font/image/text/video sections); `extMimeMap` is its inversion.
**Invariant:** (1) The dual-overload set makes MemoryBlobCRUD drop-in compatible both with hash-addressed stores (server blobs) and explicit-id stores. (2) Extension derivation NEVER invents data: unknown-but-present types degrade to their own subtype string. (3) Missing blob in getAssetName THROWS (`'blob not found for blobId: <id>'`) — callers rely on this fail-fast rather than empty names.
**Probe:** `grep -o "'application/[a-z0-9.+-]*'" …store/src/adapter/assets.ts | wc -l` → `38`. And `grep -n 'getExt = ' …adapter/assets.ts | cut -d: -f1` → `135`. Direct tests: `src/__tests__/assets.unit.spec.ts` pins all naming branches incl. octet-stream→`.bin`, empty-type→`.blob`, and the BlockSuiteError throw.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-affine", query: "MemoryBlobCRUD mimeExtMap getAssetName extMimeMap", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt as the reference stub for testing any snapshot+assets pipeline, and the name ladder for zip/html exporters. Adapt the table to your platform's mime registry. Omit the verbatim-name rule and user-named attachments get silently renamed on round-trip.
