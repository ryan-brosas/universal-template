<!-- capsule-v2 -->
# AssetsManager blob ladder — how are blobs deduplicated, renamed, and type-repaired during export?

**Source:** AFFiNE MIT `canary@<pin>`; Codebase Memory `ext-affine`. **Question:** What happens when two exported images share a filename, or when a stored blob lost its MIME type?

## Read/write asset pipeline with name-conflict and MIME-guess ladders
**Path/Symbol:** `blocksuite/framework/store/src/transformer/assets.ts:21-105` (`AssetsManager`), :10-19 (`makeNewNameWhenConflict`), read ladder :61-92.
**Signature:** `readFromBlob(blobId: string): Promise<void>` / `writeToBlob(blobId: string): Promise<void>` (throws `BlockSuiteError 'Blob <id> not found in assets manager'`); state: `_assetsMap: Map<blobId, Blob>`, `_names: Set<string>`, `_pathBlobIdMap`.
**Data Shape:** `uploadingAssetsMap: Map<blockId, { blob, abortController?, mapInto }> ` — the block-keyed side-channel consumed by upload middleware.

### Decisive source
```ts
// assets.ts:68-91 — three-tier classification of every fetched blob
if (blob instanceof File) {
  let file = blob;
  if (this._names.has(blob.name)) {
    const newName = makeNewNameWhenConflict(this._names, blob.name);
    file = new File([blob], newName, { type: blob.type });   // "name (1).ext"
  }
  this._assetsMap.set(blobId, file);
  this._names.add(file.name);
  return;
}
if (blob.type && blob.type !== 'application/octet-stream') {
  this._assetsMap.set(blobId, blob);                          // trusted type
  return;
}
const buffer = await blob.arrayBuffer();                      // dynamic import!
const FileType = await import('file-type');
const fileType = await FileType.fileTypeFromBuffer(buffer);
if (fileType) { this._assetsMap.set(blobId, new File([blob], '', { type: fileType.mime })); return; }
this._assetsMap.set(blobId, blob);                            // last resort: as-is
```

**Flow:** export hooks call `assetsManager.readFromBlob(id)` lazily per referenced blob → cached in `_assetsMap` → adapters serialize via `getAssetName()` → importers write back with `writeToBlob`. `Transformer.reset()`/`[Symbol.dispose]()` clear maps so one manager instance can serve repeated conversions without stale names.
**Invariant:** (1) Name conflicts rename the COPY, never the original — `makeNewNameWhenConflict` loops ` (i)` suffixes on the extension only. (2) `application/octet-stream` is treated as UNKNOWN, not as a type: it triggers buffer sniffing via a **dynamic** `import('file-type')` (keeps it out of non-sniffing bundles). (3) `cleanup()` clears `_assetsMap` + `_names` but NOT `uploadingAssetsMap` — in-flight uploads survive transformer disposal by design.
**Probe:** `grep -n 'fileTypeFromBuffer\|octet-stream\|makeNewNameWhenConflict' …transformer/assets.ts | cut -d: -f1` → `10 71 78 85`. Direct tests: `src/__tests__/assets.unit.spec.ts:5-77` pins `getAssetName` naming ladder incl. `'blobId.bin'` for octet-stream, `'blobId.blob'` for empty type, and BlockSuiteError throw for missing id.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-affine", query: "AssetsManager readFromBlob file type guess name conflict", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the File/Blob/trusted-MIME/sniff ladder for any snapshot+assets exporter. Adapt the conflict-suffix format to your platform's conventions. Omit the octet-stream sniff and every re-imported legacy blob renders as broken downloads.
