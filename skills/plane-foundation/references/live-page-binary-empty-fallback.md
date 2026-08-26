<!-- capsule-v2 -->
# Empty-binary page fetch with legacy-HTML fallback — how do you serve a CRDT document when storage has no Yjs binary yet?

**Source:** plane AGPL-3.0-only `preview@e056bbf9eb6b511cdc0a5823b1bd6922e561a485`; Codebase Memory `plane`. **Question:** A porter adding live collaboration over an existing HTML-content store must answer: what does `onLoadDocument` return when the stored binary is zero bytes, and what happens if the one-time migration write-back fails?

## Fetch fallback ladder
**Path/Symbol:** `apps/live/src/extensions/database.ts:fetchDocument` (:26–70), backed by `apps/live/src/services/page/core.service.ts:PageCoreService.fetchDescriptionBinary` (:41–62).
**Signature:** `fetchDocument({ context, documentName: pageId, instance }): Promise<Uint8Array>`; `fetchDescriptionBinary(pageId): Promise<Buffer>` (axios `responseType: "arraybuffer"`, `Content-Type: application/octet-stream`).
**Data Shape:** Stored payload is a binary blob (`description_binary`); legacy pages carry only `description_html` + `name`. Service selection is per-connection via `getPageService(context.documentType, context)` — currently only `"project_page"` is accepted; anything else throws.

### Decisive source
```ts
const response = (await service.fetchDescriptionBinary(pageId)) as Buffer;
const binaryData = new Uint8Array(response);
if (binaryData.byteLength === 0) {
  const pageDetails = await service.fetchDetails(pageId);
  const convertedBinaryData = getBinaryDataFromDocumentEditorHTMLString(
    pageDetails.description_html ?? "<p></p>", pageDetails.name
  );
  if (convertedBinaryData) {
    try { /* ...re-encode all formats... */ await service.updateDescriptionBinary(pageId, payload); }
    catch (e) { logger.error("Failed to save binary after first conversion from html:", error); }
    return convertedBinaryData;
  }
}
return binaryData;
```

**Flow:** GET binary → if `byteLength === 0`, fetch page details → convert `description_html` (defaulting to `<p></p>`) into a Yjs doc seeded with the page name → attempt write-back of all three formats (binary/html/json) **fail-soft** (log only) → return converted bytes. On ANY fetch error: wrap in AppError, broadcast a typed `error` realtime event ("Unable to load the page. Please try refreshing.", type `"fetch"`) to the room, then rethrow so hocuspocus aborts the load.
**Invariant:** The user-visible session never dies because the migration write-back failed — conversion failure still returns the converted document; only upstream fetch failure is fatal. The empty-binary sentinel is `byteLength === 0` on the raw buffer, checked BEFORE any parsing.
**Probe:** No dedicated upstream test. Deterministic pin: database.ts contains the literal `binaryData.byteLength === 0` branch and the fail-soft log string "Failed to save binary after first conversion from html:"; core.service.ts throws `new Error("Expected response to be a Buffer")` on non-buffer data.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "plane", query: "fetchDescriptionBinary page description binary arraybuffer", limit: 5 });
```
Observed at pin: rank-2 = `PageCoreService.fetchDescriptionBinary` (core.service.ts :41–62); note the web frontend twin at apps/web ranks above it — scope citations by file path.

## Verdict
Adopt the lazy one-time HTML→CRDT migration with best-effort write-back and user-facing error broadcast on fatal fetch; adapt the converter functions (`@plane/editor`) to your editor's serializer; omit Plane's dual service dispatch until more document types exist. Coverage caveat: paths clean @ gen 2026-08-25T19:59:48Z; no upstream tests cover this ladder.
