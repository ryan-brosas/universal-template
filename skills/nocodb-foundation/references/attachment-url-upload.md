<!-- capsule-v2 -->
# Attachment URL upload job — how does a paste-a-URL attachment update get fetched and stored off the request path?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** How is the URL→storage transfer delegated to the worker, and where does the actual work live?

## thin processor delegating to service
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/attachment-url-upload/attachment-url-upload.processor.ts:AttachmentUrlUploadProcessor.job` (whole, 15 lines); real logic `~/services/v3/data-attachment-v3.service.ts:DataAttachmentV3Service.handleUrlUploadCellUpdate`.
**Signature:** `job(job: Job<AttachmentUrlUploadJobData>): Promise<void>` — one delegation line; SKIP_STORING_JOB_META does NOT include this type (it gets an nc_jobs row).
**Data Shape:** payload carries the cell-update context (base/source/table/column/row + URL list) so the worker can re-derive everything.

### Decisive source
```ts
@Injectable()
export class AttachmentUrlUploadProcessor {
  constructor(private readonly dataAttachmentV3Service: DataAttachmentV3Service) {}
  async job(job: Job<AttachmentUrlUploadJobData>) {
    await this.dataAttachmentV3Service.handleUrlUploadCellUpdate(job.data);
  }
}
```

**Flow:** the v3 API accepts attachment-by-URL cell updates, validates, then enqueues; the worker fetches each URL, writes bytes through the storage adapter, and updates the cell's attachment metadata. Keeping the fetch off-process protects API latency from slow/huge remote files.
**Invariant:** the processor owns NO business logic — it exists purely to give the queue a registered entry point with DI services. Payload must be self-sufficient (ids + urls), because the originating request is long gone by execution time. Errors thrown here surface through normal Bull retry/failed handling since this type IS meta-stored.
**Probe:** no unit test upstream. Source-grounded probe: single-delegation body at `attachment-url-upload.processor.ts:12-14`; absence from the SKIP_STORING_JOB_META array (`interface/Jobs.ts:99-128`) confirms meta-row tracking.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "AttachmentUrlUploadProcessor handleUrlUploadCellUpdate", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt thin-processor/delegating-service split for backgrounded request work; adapt the service contract to your storage stack; omit the v3-specific cell schema. Coverage caveat: no in-repo tests; source-grounded.
