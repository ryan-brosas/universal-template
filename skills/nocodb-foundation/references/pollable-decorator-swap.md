<!-- capsule-v2 -->
# Pollable fire-and-poll decorator — how does a service method become "returns {id} now, result via /jobs/listen later" while the processor still calls the real body?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** How does @Pollable wrap a method into a job enqueue WITHOUT breaking the worker that executes it?

## Decorator swap + __original escape hatch
**Path/Symbol:** `packages/nocodb/src/decorators/pollable.decorator.ts:Pollable` (:25–:65 whole file 65L) · args serialization `helpers/serialize-worker-args.ts:serializeWorkerArgs` (:17–:46 whole).
**Signature:** `Pollable(): MethodDecorator`; wrapped fn returns `{id: job.id}`; jobId = `'job' + nanoid(14, [0-9a-z])`.
**Data Shape:** payload `{service: <ClassName>, method: <name>, args: serializedArgs}` under `JobTypes.UseWorker`; `wrappedFn['__original'] = originalMethod` is the ONLY legal re-entry.

### Decisive source
```ts
const serializedArgs = serializeWorkerArgs(args, method, service);
const jobId = `job${nanoidv2()}`;
const job = await nocoJobsService.add(
  JobTypes.UseWorker,
  { service, method, args: serializedArgs },
  { jobId },
);
return { id: job.id };
// ...
// Store original so UseWorkerProcessor can bypass the decorator
wrappedFn['__original'] = originalMethod;
```
(:44–:59)

**Flow:** decorator injects NocoJobsService onto the instance (`this._nocoJobsService`) → wrapped fn serializes args (functions THROW immediately — never valid in a job; objects JSON-roundtripped with circular replacer; unserializable objects become `undefined` with a warning) → enqueue → caller gets `{id}` instantly and polls `/jobs/listen` (jobs-polling capsule owns that half) → worker side calls `target.__original || target` so executing the job does NOT re-enqueue.
**Invariant:** missing service ⇒ SYNCHRONOUS fallback execution with a warn ("should not happen in production") — degradation, not failure; the `__original` unwrap is load-bearing (infinite re-enqueue otherwise — use-worker-rpc capsule pins the consumer half). serializeWorkerArgs' function-throw must precede any enqueue so bad payloads fail at the CALL SITE, not inside a ghost job.
**Probe:** `cd packages/nocodb && grep -n "__original" src/decorators/pollable.decorator.ts` (:23 comment + :59 assignment, single pair) and `grep -c "throw new Error(msg)" src/helpers/serialize-worker-args.ts` (=1 function-arg rejection site).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "Pollable serializeWorkerArgs __original JobTypes.UseWorker nanoidv2", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the swap-with-escape-hatch pattern and call-site fail-fast arg validation; adapt queue client and id alphabet; omit the sync-fallback only if you prefer hard failure when DI wiring breaks. Coverage caveat: no spec; count-pinned greps.
