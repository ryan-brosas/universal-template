<!-- capsule-v2 -->
# Job log fan-out — how do processors stream progress lines to a UI while a job runs, without touching the queue library?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** What is the logging contract every processor uses, and how is it transported?

## EventEmitter LOG + jobs-log service
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/jobs-log.service.ts:JobsLogService.sendLog` (whole, 16 lines); `src/interface/Jobs.ts:JobEvents` (141-144); consumers e.g. `meta-sync.processor.ts:32-35`, `data-import.processor.ts:161-166`.
**Signature:** `sendLog(job: Partial<Job>, data: {message: string}): void`; event name `JobEvents.LOG = 'job.log'` (status twin `JobEvents.STATUS = 'job.status'`).
**Data Shape:** `{id: job.id.toString(), data: {message}}`; structured messages are `JSON.stringify({status: 'progress'|'completed', ...counters})`.

### Decisive source
```ts
@Injectable()
export class JobsLogService {
  constructor(private eventEmitter: EventEmitter2) {}
  sendLog(job: Partial<Job>, data: { message: string }) {
    this.eventEmitter.emit(JobEvents.LOG, { id: job.id.toString(), data });
  }
}
// processor-side closure pattern:
const logBasic = (log) => {
  this.jobsLogService.sendLog(job, { message: log });   // to listeners
  this.debugLog(log);                                    // and to debug stdout
};
```

**Flow:** any processor emits a log line through the service; the jobs-event layer (pass-1 `jobs-events.md`) subscribes on `job.log`, appends to the `_mid`-indexed message log and pushes it into the long-poll room for that job id. Importers additionally emit JSON status objects (`{status:'progress', rowsInserted, totalProcessed...}`) that the UI parses into progress bars.
**Invariant:** `job.id.toString()` — Bull ids may be numbers; listeners key rooms by string. Logging must never await or throw into the processor's hot path (emit is fire-and-forget). The dual closure (sendLog + debugLog) keeps worker stdout greppable while serving live UI.
**Probe:** no unit test upstream. Source-grounded probe: `jobs-log.service.ts:8-14` — emit-only body; `data-import.processor.ts:771-784` — reportProgress JSON shape.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "JobsLogService sendLog JobEvents LOG eventEmitter", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the emit-only log micro-service with string-keyed job ids and structured progress JSON; adapt transport (your pub-sub/SSE) around the same contract; omit NestJS EventEmitter2 if your DI differs. Coverage caveat: no in-repo tests; source-grounded.
