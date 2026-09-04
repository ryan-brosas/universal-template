<!-- capsule-v2 -->
# UseWorker RPC — how does the API layer run an arbitrary service method on the worker container instead of in the web process?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** How is a decorator-turned-async call dispatched to a queue job that invokes the real method remotely?

## service+method+args envelope with __original bypass
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/use-worker/use-worker.processor.ts:UseWorkerProcessor.job/serviceMap` (whole, 53 lines); SKIP_STORING_JOB_META includes `JobTypes.UseWorker` (`src/interface/Jobs.ts:102`).
**Signature:** `job(job: Job<{service: string; method: string; args: any[]}>): Promise<any>`; `protected get serviceMap(): Record<string, any>`.
**Data Shape:** payload `{service: 'AttachmentsService', method: '...', args: [...]}` (class-name keys); result = whatever the method returns, serialized through Bull.

### Decisive source
```ts
// Use __original to bypass @Pollable/@UseWorker decorator and call the real method
const fn = target.__original || target;
return fn.apply(processor, args);
```

**Flow:** client side, `@UseWorker` decorators wrap service methods so calling them enqueues `{service, method, args}` instead of executing. The worker's processor looks up the registered service by class name, resolves the method, unwraps any decorator wrapper via `__original`, and applies it locally. Missing service/method throw descriptive errors listing valid names.
**Invariant:** `__original || target` is load-bearing — invoking the decorated function inside the worker would RE-enqueue the job infinitely (the decorator fires again). The serviceMap must be an explicit allowlist; arbitrary class resolution would be RCE. Job type is in SKIP_STORING_JOB_META so these RPCs don't create nc_jobs rows.
**Probe:** no unit test upstream. Source-grounded probe: `use-worker.processor.ts:40-53` — lookup ladder ending in `fn.apply(processor, args)` with the bypass comment; `interface/Jobs.ts:99-103` — UseWorker in the skip list.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "UseWorkerProcessor serviceMap __original Pollable", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the allowlisted name-based RPC envelope and the original-fn unwrap pattern for decorator-duplicated methods; adapt transport (Bull vs your queue) and allowed services; omit @Pollable status-polling integration unless porting the decorator pair together. Coverage caveat: no in-repo tests; source-grounded.
