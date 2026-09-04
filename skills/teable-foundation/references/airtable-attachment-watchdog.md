<!-- capsule-v2 -->
# Airtable attachment transfer watchdog — how do you move CDN files into object storage without leaking sockets or hanging forever?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** What is the correct stream pipeline + stall-timeout choreography for streaming a remote attachment straight into a storage backend (no temp file), including the pre-consumer race windows?

## Stream transfer with inactivity watchdog
**Path/Symbol:** `apps/nestjs-backend/src/features/airtable-import/airtable-import.service.ts`:`transferAttachment` (:1012–1099).
**Signature:** `private async transferAttachment(attachment: IAirtableAttachment)` → resolves to the stored-attachment item.
**Data Shape:** Airtable supplies `size` up front (required by presigned upload); `attachmentConcurrency = 3` bounds parallel cell transfers via `mapWithConcurrency`; per-field failure aggregation `{count, firstError(200 chars)}` becomes a `valuesDropped` issue.

### Decisive source
```ts
const stalled = new Promise<never>((_, reject) => { onStall = reject; });
// The watchdog can fire while the fetch below is still awaiting headers,
// before Promise.race() observes this promise — keep the rejection handled.
stalled.catch(() => undefined);
...
// pipeline() into the monitor rather than a bare on('data') listener: a
// data listener would start the flow before uploadFromStream attaches
// its consumer and silently drop those chunks, while the Transform
// buffers them with backpressure.
pipeline(Readable.fromWeb(response.body as any), monitor, (error) => {
  if (error) onStall(error);
});
const upload = this.attachmentsService.uploadFromStream(monitor, {...}, UploadType.Table,
  { signal: controller.signal });
upload.catch(() => undefined);   // losing side must not become an unhandled rejection
try { return await Promise.race([upload, stalled]); }
catch (error) { monitor.destroy(); throw error; }  // release the still-open CDN socket
```

**Flow:** pre-flight size rejection BEFORE opening the socket (`maxOpenapiAttachmentUploadSize`) → fetch with abort signal → non-ok ⇒ `response.body.cancel()` (expired CDN links are common — release the socket) → content-length must be finite or abort → `pipeline(download, Transform-monitor)` where the monitor's transform refreshes `stallTimer` on every chunk → race upload vs stalled → finally `clearTimeout`.
**Invariant:** The watchdog fires only when NO bytes move for `attachmentStallTimeoutMs = 60_000` (a slow-but-flowing transfer of any size is never interrupted). Three unhandled-rejection windows are each explicitly defused: stalled-before-race (`stalled.catch`), monitor-error-before-pipeline (`monitor.on('error')`), and losing-upload-after-watchdog (`upload.catch`). The same signal cancels the storage PUT after the download drains (destroying an ended stream cannot).
**Probe:** `grep -cF "stalled.catch" apps/nestjs-backend/src/features/airtable-import/airtable-import.service.ts` returns 1; `grep -cF "attachmentStallTimeoutMs" ...` returns 3.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"teable","query":"transferAttachment stallTimer uploadFromStream AbortController","limit":5,"detail":"ids"}'
```

## Verdict
Adopt the chunk-refresh stall watchdog + triple unhandled-rejection armor + size-preflight for any remote-to-storage stream; adapt limits and storage API; omit teable's attachment service internals. Coverage caveat: none.
