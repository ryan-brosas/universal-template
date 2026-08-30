<!-- capsule-v2 -->
# Import attachment streaming — why does the importer open a temp-file stream instead of buffering the upload, and what is the cleanup contract?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** How does the import job receive its uploaded file and guarantee deletion even when the import throws?

## openImportAttachmentStream + finally-cleanup
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/data-import/attachment-stream.ts:openImportAttachmentStream/deleteImportAttachment` (referenced `data-import.processor.ts:23-27`); cleanup call at `data-import.processor.ts:run` finally block (320-328).
**Signature:** `openImportAttachmentStream(importType, attachment, encoding): Promise<Readable>`; `deleteImportAttachment(attachment): Promise<void>`; `run(..., opts: {cleanupAttachment?: boolean} = {})`.
**Data Shape:** `attachment = {title, path|url}`; handlers consume the Readable; AI-chat path calls `run()` directly with `cleanupAttachment: false`.

### Decisive source
```ts
} finally {
  if (opts.cleanupAttachment !== false) {
    try { await deleteImportAttachment(attachment); }
    catch (e) { this.logger.warn(`Failed to cleanup temp file: ${e.message}`); }  // never mask
  }
}
```

**Flow:** the HTTP layer streams the multipart upload to a temp location and enqueues the job with only its reference; the worker opens a fresh Readable per sheet pass (`streamSheetData` calls openImportAttachmentStream once per sheet), handlers parse from it, and the outermost `finally` deletes it — on success AND failure.
**Invariant:** cleanup failures are WARN-logged, never rethrown — a temp file leak must not turn a successful import into a failed one. The `cleanupAttachment !== false` opt-out exists because the synchronous in-process caller (AI chat tool) owns the file lifecycle. One stream per sheet invocation keeps parser offsets independent.
**Probe:** no unit test upstream. Source-grounded probe: `data-import.processor.ts:320-328` — finally block with swallow-and-warn; `:174-178` — run() signature exposing the opt-out.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "openImportAttachmentStream deleteImportAttachment cleanupAttachment", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt reference-passed attachments with finally-block cleanup and warn-only failure; adapt storage/temp paths and the opt-out flag to host; omit per-type stream opening if your parser takes a path. Coverage caveat: no in-repo tests; source-grounded.
