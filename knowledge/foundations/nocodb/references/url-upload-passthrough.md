<!-- capsule-v2 -->
|# AttachmentUrlUpload processor — the 15-line pass-through delegation

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f751366`; Codebase Memory project `nocodb`. **Question:** The thinnest processor in the jobs module — what makes a pure-delegation job worth its own JobType?

## Path/Symbol
`packages/nocodb/src/modules/jobs/jobs/attachment-url-upload/attachment-url-upload.processor.ts` (whole file, 15 L); producer `services/emit-handler/attachment-url-upload.handler.ts:25`.

**Signature:** `job(job: Job<AttachmentUrlUploadJobData>) { await this.dataAttachmentV3Service.handleUrlUploadCellUpdate(job.data); }`.

**Data Shape:** zero transformation — payload captured by the emit-handler passes through untouched to the v3 attachment service.

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

**Flow:** URL-attachment cell update detected → emit-handler captures full context → enqueue (meta-stored job type) → processor delegates verbatim → service performs fetch/store/thumbnail chain.

**Invariant:** (1) The indirection exists so an HTTP-triggered cell update can run OUTSIDE the request lifecycle without the service knowing about queues — the queue boundary is the point. (2) Pass-through payloads keep ONE serialization of the job contract; reshaping here would fork the schema between enqueue-time and execute-time copies. (3) Own JobType ⇒ own admission identity (local concurrency, version stamp) even with a one-line body.

**Probe:** no unit test upstream. Source-grounded probe: whole file cited above; pairing capsules attachment-url-upload.md + internal-event-job-enqueue.md.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "AttachmentUrlUploadProcessor handleUrlUploadCellUpdate", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt pass-through delegation processors when moving sync work off-request; adapt service names; omit nothing. Coverage caveat: no in-repo unit tests; source-grounded.
