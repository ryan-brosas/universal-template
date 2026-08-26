<!-- capsule-v2 -->
# In-memory job worker twin — what EXACTLY must setTimeout-based workers emulate from a real queue?

**Source:** grist-core MIT `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** When Redis is absent every job must be produced and consumed in-process — what semantics does the fake worker preserve, and where does it deliberately diverge?

## Direct-callback worker keyed by jobId; delay/repeat as timer handles; clearJob clears BOTH timer kinds
**Path/Symbol:** `app/server/lib/GristJobs.ts`: `GristWorker` (300–350): `_jobs Map<string, NodeJS.Timeout>` (:301), `close()` (307–312), `add(name, data, options)` (314–334), `obliterate()` (= close, 336–338), `_clearJob` (340–349); scope-side guard `GristInMemoryQueueScope.add` throws without handler (226–233).
**Signature:** `add(name: string, data: any, options?: { delay?, jobId?, repeat?: {every} })`; `close(): Promise<void>`.
**Data Shape:** timer map keyed by `options.jobId || makeId()`; immediate jobs bypass the map entirely.

### Decisive source
```ts
public async add(name: string, data: any, options?: JobAddOptions) {
  if (options?.delay) {
    if (options.repeat) { throw new Error("cannot delay and repeat"); }
    const jobId = options.jobId || makeId();
    this._clearJob(jobId);                       // re-add = replace, like re-enqueue
    this._jobs.set(jobId, setTimeout(() => this._callback({ name, data }), options.delay));
    return;
  }
  if (options?.repeat) {
    const jobId = options.jobId || makeId();
    this._clearJob(jobId);
    this._jobs.set(jobId, setInterval(() => this._callback({ name, data }), options.repeat.every));
    return;
  }
  await this._callback({ name, data });          // immediate: NO queue hop at all
}
private _clearJob(id: string) {
  ...
  // We don't know if the job is a once-off or repeating,
  // so we call both clearInterval and clearTimeout, which apparently works.
  clearInterval(job); clearTimeout(job);
  this._jobs.delete(id);
}
```

**Flow:** immediate jobs execute INLINE through the handler promise (no ordering guarantees beyond JS task order — there is no pending list); delayed/repeating jobs become timer handles so `stop()/obliterate()` can cancel them deterministically in tests; re-adding the same jobId replaces the prior timer (idempotent scheduling); closing iterates the live map while deleting from it via the keys() iterator (safe).
**Invariant:** this twin exists so the SAME tests pass without redis — it preserves add/handle/stop semantics but NOT persistence, retries, or cross-process delivery (documented "very crude"; upstream comment admits the divergence "could be elaborated if needed"). Delay+repeat together is rejected rather than silently mis-scheduled. Timer-handle clearing relies on the Timeout object being accepted by both clear functions.
**Probe:** same suite's "without redis" block pins behavior: `test/server/lib/GristJobs.ts:27` covering immediate :41, delayed :73, repeated :100, restart-of-worker pickup :127.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "GristWorker obliterate setInterval repeat delayed jobs in memory", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt as the reference shape for a test-friendly no-infra queue stub: inline execution, timer-backed delay/repeat, jobId replacement, cancel-everything shutdown. Adapt by adding concurrency limits or persistence only if your single-process mode needs them. Omit nothing if you want test parity — the both-clears trick and reject-on-unhandled-add are load-bearing.
