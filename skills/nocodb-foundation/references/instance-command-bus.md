<!-- capsule-v2 -->
# Instance command bus — how do primary and worker instances send control commands to each other over Redis pub-sub without a request/response protocol?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** How do primary and worker instances exchange control commands (pause/resume local queue, abort streams) over pub-sub?

## JobsRedis command bus + publish-as-count
**Path/Symbol:** `packages/nocodb/src/modules/jobs/redis/jobs-redis.ts:JobsRedis.initJobs/workerCount/emitWorkerCommand` (17-100); `packages/nocodb/src/interface/Jobs.ts:InstanceTypes/InstanceCommands` (174-186).
**Signature:** `initJobs(): Promise<void>`; `workerCount(): Promise<number>`; `emitWorkerCommand(command: InstanceCommands, ...args: string[]): Promise<void>`.
**Data Shape:** wire message = `command[:arg1:arg2...]` (colon-joined string); channels = `${NC_ENV}-primary` / `${NC_ENV}-worker`; callbacks registry = static `workerCallbacks`/`primaryCallbacks` maps filled by consumers.

### Decisive source
```ts
const onMessage = async (channel, message) => {
  const args = message.split(':');
  const command = args.shift();
  if (channel === InstanceTypes.WORKER) {
    this.workerCallbacks[command] && (await this.workerCallbacks[command](...args));
  } else if (channel === InstanceTypes.PRIMARY) { ... }
};
// a worker subscribes to its own channel; a non-worker subscribes to PRIMARY
if (process.env.NC_WORKER_CONTAINER === 'true') {
  await PubSubRedis.subscribe(InstanceTypes.WORKER, ...);
} else {
  await PubSubRedis.subscribe(InstanceTypes.PRIMARY, ...);
}
// workerCount = number of Redis subscribers that received the 'count' publish
return new Promise((resolve) => {
  PubSubRedis.redisClient.publish(InstanceTypes.WORKER, 'count', (error, n) =>
    error ? resolve(0) : resolve(n));
});
```

**Flow:** emit → `PUBLISH <type-channel> command:args`; every instance of the *other* type receives it and dispatches through its static callback map. Worker liveness uses the same channel: publishing `'count'` returns the subscriber count as the callback arg — zero infrastructure beyond PUBLISH's return value.
**Invariant:** an instance NEVER subscribes to the channel it publishes commands for — workers listen on WORKER, primaries on PRIMARY. `workerCount()` is advisory (a worker that started subscribing counts even if wedged), so it gates only queue pausing, not data integrity. Command names are registry-dispatched; unknown commands are silently ignored (`cb && await cb(...)`), making old/new version skew during rolling deploys safe.
**Probe:** no unit test upstream. Source-grounded probe: `jobs-redis.ts:52-60` — mutually exclusive subscribe branch keyed on NC_WORKER_CONTAINER; `:73-87` — resolve from the publish ack, never from a reply message.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "JobsRedis initJobs workerCount emitWorkerCommand", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-role channel scheme, colon-packed command frames, callback-map dispatch, and publish-ack worker counting; adapt channel prefixes/env detection and the command enum to host; omit EE commands unless porting worker groups. Underlying transport is PubSubRedis (`src/redis/pubsub-redis.ts`) — single demuxed 'message' listener with refcounted per-channel handler sets and unsubscribe handles; adopt that shape when many modules share one channel. Coverage caveat: no in-repo tests; source-grounded.
