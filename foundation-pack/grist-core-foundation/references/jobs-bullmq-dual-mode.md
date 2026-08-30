<!-- capsule-v2 -->
# BullMQ/in-memory job queue twin — how do you make Redis-backed queues optional at runtime?

**Source:** grist-core MIT `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** Queues are handy but requiring Redis excludes single-binary installs — how do you structure one queue API over BullMQ AND a zero-dependency fallback?

## GristJobs interface with lazy per-name scopes; REDIS_URL presence selects implementation; identical handleName/handleDefault protocol
**Path/Symbol:** `app/server/lib/GristJobs.ts`: `GristJobs`/`GristQueueScope` interfaces (36–82), `createGristJobs` selector (117–120), `GristJobsBase` scope map (122–133), `getRedisConnection` (170–185), `GristBullMQJobs` (144–165), `GristBullMQQueueScope.add` retention (254–267), `GristQueueScopeBase` named-processor registry (191–223); queue-name centralization `docEmailsQueue/deliveryLogKey/batchJobKey/batchPayloadKey` (11–16).
**Signature:** `createGristJobs(): GristJobs`; `scope.queue(name?) → { add(name, data, {delay?, jobId?, repeat?:{every}}), handleDefault(cb), handleName(name, cb), stop({obliterate?}) }`.
**Data Shape:** `DEFAULT_QUEUE_NAME = "default"`; test isolation prefix `GRIST_TEST_REDIS_QUEUE_PREFIX` read DYNAMICALLY (`getQueuePrefix()` fn not const) so tests can set env after module load.

### Decisive source
```ts
export function createGristJobs(): GristJobs {
  const connection = getRedisConnection();
  return connection ? new GristBullMQJobs(connection) : new GristInMemoryJobs();
}
// BullMQ add defaults — retention policy is part of the port:
removeOnComplete: { age: 3600, count: 1000 },   // 1 hour / 1000 jobs
removeOnFail:     { age: 24 * 3600 },
...
const conn = new IORedis(urlTxt, {
  maxRetriesPerRequest: null,
  retryStrategy: times => Math.min((times ** 2) * 50, 10000), // back off faster, retry slower
});
// handleDefault routes recognized names to handleName handlers first:
const callback = async (job: Job) => {
  const processor = this._namedProcessors[job.name] || defaultCallback;
  return processor(job);
};
```

**Flow:** process startup calls createGristJobs once → each consumer asks for a NAMED scope (`queue("deq")`) which is memoized per name → producers `add()` immediately; consumers must call handleName for specific jobs and handleDefault to ACTIVATE the worker ("no job handling will happen until handleDefault has been called") → stop() fans out to every scope then closes the shared connection. Queue NAMES are centralized in this file "to ensure that different users of GristJobs don't accidentally use conflicting queue names".
**Invariant:** the two implementations are behaviorally pinned by THE SAME test suite run twice (with/without redis) — any semantic you add must exist in both; jobs may outlast the process (BullMQ side), which shapes testing/deployment; the in-memory twin throws on add-before-handler rather than silently dropping.
**Probe:** `test/server/lib/GristJobs.ts:20/:27` "with redis"/"without redis" describe blocks running identical ladders — immediate :41, delayed :73, repeated :100, pick-up-again :127.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "createGristJobs GristBullMQQueueScope handleDefault docEmailsQueue", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt when background work should degrade gracefully without infra: define the narrow scope interface, centralize queue names, keep retention defaults in the adapter. Adapt retry/backoff numbers and retention windows to your SLAs. Omit the repeat/every support if your scheduler layer already covers it.
