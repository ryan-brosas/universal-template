<!-- capsule-v2 -->
# CCR worker init/epoch handshake — how does a spawned worker register against a session API with a typed failure ladder and stale-state cleanup?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** What must a long-lived worker do at startup to claim its slot (epoch), restore prior state, and fail loudly — without leaking timers when the claim loses?

## Typed init errors over a two-source epoch
**Path/Symbol:** `src/cli/transports/ccrClient.ts`: `CCRInitFailReason`/:49-52, `CCRInitError`/:55-59, `initialize`/:459-526, `getWorkerState`/:530-548, default `onEpochMismatch`/:294-300; consumer wiring `src/cli/remoteIO.ts`:127-137.
**Signature:** `initialize(epoch?: number): Promise<Record<string, unknown> | null>`; reasons `'no_auth_headers' | 'missing_epoch' | 'worker_register_failed'`; constructor opts `{ onEpochMismatch?: () => never }`.
**Data Shape:** epoch from explicit arg (in-process replBridge — it registered the worker itself, no parent env) else `parseInt(process.env.CLAUDE_CODE_WORKER_EPOCH)`; init PUT body `{ worker_status:'idle', worker_epoch, external_metadata:{ pending_action:null, task_summary:null } }`.

### Decisive source
```ts
const result = await this.request('put', '/worker', {
  worker_status: 'idle',
  worker_epoch: this.workerEpoch,
  // Clear stale pending_action/task_summary left by a prior
  // worker crash — the in-session clears don't survive process restart.
  external_metadata: { pending_action: null, task_summary: null },
}, 'PUT worker (init)')
if (!result.ok) {
  // 409 → onEpochMismatch may throw, but request() catches it and returns
  // false. Without this check we'd continue to startHeartbeat(), leaking a
  // 20s timer against a dead epoch. Throw so connect()'s rejection handler
  // fires instead of the success path.
  throw new CCRInitError('worker_register_failed')
}
this.currentState = 'idle'; this.startHeartbeat()
```
```ts
// Concurrent GET of prior state — logged AFTER the PUT succeeds:
// "logging inside getWorkerState() raced: if the GET resolved before the
// PUT failed, diagnostics showed both init_failed and state_restored."
const restoredPromise = this.getWorkerState()   // launched before PUT
...
const { metadata } = await restoredPromise      // awaited after success path
```

**Flow:** auth-header presence check → epoch resolve (arg > env, NaN ⇒ throw) → launch getWorkerState() concurrently → init PUT → ok? start heartbeat + register keep-alive activity callback : await restored and log `state_restored` ; !ok ⇒ CCRInitError so remoteIO's catch logs `cli_worker_lifecycle_init_failed {reason}` and gracefulShutdown(1). remoteIO stores `restoredWorkerState = init.catch(() => null)` so downstream consumers DEGRADE to null instead of rejecting.
**Invariant:** Every init failure is TYPED for the diagnostics classifier. The 409-superseded case MUST rethrow inside initialize because request() swallows it into `{ok:false}` — skipping that check leaks a live heartbeat timer against a dead epoch. Default `onEpochMismatch` is `process.exit(1)` (correct only for spawn-mode children the parent bridge re-spawns); in-process callers MUST override or exit kills the user's REPL. Init PUT writes explicit NULLS to clear crashed-worker leftovers — absent keys would preserve them.
**Probe:** `grep -n "'worker_register_failed'" src/cli/transports/ccrClient.ts` (`:52` region + throw site `:496`), `grep -n "leaking a" src/cli/transports/ccrClient.ts` (`:493` comment), `grep -n "pending_action: null" src/cli/transports/ccrClient.ts` (`:485`), `grep -n "process.exit(1)" src/cli/transports/ccrClient.ts` (`:329`). No upstream unit tests — deterministic anchors are the probe tier.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", name_pattern: "^(initialize|CCRInitError|getWorkerState)$", file_pattern: "**/ccrClient.ts", limit: 5 });
// initialize :459-526 · getWorkerState :530-548 · CCRInitError :55-59 (executed live pre-write)
```

## Verdict
Adopt for any supervised-worker registration: typed init failures, arg>env epoch source, explicit-null crash cleanup, post-success restore logging. Adapt the epoch mechanism to your coordinator's fencing token. Omit nothing from the result.ok rethrow — it is the whole point.
