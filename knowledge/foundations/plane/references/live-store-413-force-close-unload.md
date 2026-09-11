<!-- capsule-v2 -->
# Store-error triage: 413 force-close-and-swallow — what does the server do when a collaborative save exceeds the backend's size limit?

**Source:** plane AGPL-3.0-only `preview@e056bbf9eb6b511cdc0a5823b1bd6922e561a485`; Codebase Memory `plane`. **Question:** When the debounced CRDT→API save fails, which failures disconnect everyone and unload the document, and why must that path NOT rethrow?

## Store triage ladder
**Path/Symbol:** `apps/live/src/extensions/database.ts:storeDocument` (:72–134); consumer of `PageCoreService.updateDescriptionBinary` (:118–131) and `forceCloseDocumentAcrossServers` (force-close-handler.ts :102–202).
**Signature:** `storeDocument({ context, state: pageBinaryData, documentName: pageId, instance }): Promise<void>`.
**Data Shape:** Yjs binary state → re-encoded to `{description_binary (base64), description_html, description_json}` → PATCH to API. Failure classified via `AppError.statusCode`; error codes are the union `"content_too_large" | "page_locked" | "page_archived"`.

### Decisive source
```ts
const isContentTooLarge = appError.statusCode === 413;
const shouldDisconnect = isContentTooLarge;
if (isContentTooLarge) {
  errorMessage = "Document is too large to save. Please reduce the content size.";
  errorCode = "content_too_large";
} else { errorMessage = "Unable to save the page. Please try again."; }
await broadcastError(instance, pageId, errorMessage, "store", context, errorCode, shouldDisconnect);
if (shouldDisconnect) {
  const reason = errorCode === "content_too_large" ? ForceCloseReason.DOCUMENT_TOO_LARGE : ForceCloseReason.CRITICAL_ERROR;
  const closeCode = errorCode === "content_too_large" ? CloseCode.DOCUMENT_TOO_LARGE : CloseCode.FORCE_CLOSE;
  await forceCloseDocumentAcrossServers(instance, pageId, reason, closeCode);
  // Don't throw after force close - document is already unloaded
  // Throwing would cause hocuspocus's finally block to access the null document
  return;
}
throw appError;
```

**Flow:** convert → PATCH → on failure wrap in AppError → single classification point (`statusCode === 413`) decides both the client message/errorCode and `shouldDisconnect` → always broadcast a typed `error` realtime event (type `"store"`, carries `error_code` + `should_disconnect`) → if oversized: fleet-wide force close with reason `DOCUMENT_TOO_LARGE`/close code 4001, then **return normally**; otherwise rethrow so hocuspocus's own error handling runs.
**Invariant:** After `forceCloseDocumentAcrossServers` has unloaded the document, the store callback MUST NOT throw — hocuspocus's finally block dereferences the document, so a throw there crashes on a null doc. The 413 sentinel lives on `appError.statusCode`, i.e. it depends on AppError preserving axios response status (see live-apperror-sanitization-taxonomy).
**Probe:** No dedicated upstream test. Deterministic pins: database.ts contains literally `appError.statusCode === 413`, `"content_too_large" ? CloseCode.DOCUMENT_TOO_LARGE`, and the two-line comment about hocuspocus's finally block.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "plane", query: "storeDocument updateDescriptionBinary content too large disconnect", limit: 5 });
```
Observed at pin: rank-1 = `storeDocument` (database.ts :72–134), rank-2 = `updateDescriptionBinary`.

## Verdict
Adopt the classify-once error triage with typed client payloads, the size-limit ⇒ evict-and-unload policy, and the swallow-after-unload exception contract; adapt the threshold detection (413 from your backend) and message strings; omit Plane's page_locked/page_archived enum members until your host defines them. Coverage caveat: no upstream tests for this file; behavior claims are whole-file source reads at the pinned commit.
