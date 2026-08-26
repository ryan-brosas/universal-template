<!-- capsule-v2 -->
# CCR heartbeat liveness discipline — how do you keep a lease alive across three planes without a timer firing into a closed client?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** What is the timer algebra for heartbeating against an expiring lease (20s vs 60s TTL) while staying safe against close-during-send, and what OTHER liveness planes must coexist?

## Rescheduling tick that honors close() mid-send
**Path/Symbol:** `src/cli/transports/ccrClient.ts`: `DEFAULT_HEARTBEAT_INTERVAL_MS`/:32-33, `startHeartbeat`/:677-695, `stopHeartbeat`/:698-703, `sendHeartbeat`/:706-723, activity keep-alive/:501-506, close/:982-997; sibling plane `src/cli/remoteIO.ts`:174-196; consumer drop `src/cli/structuredIO.ts`:344-347.
**Signature:** `startHeartbeat(): void`; opts `{ heartbeatIntervalMs = 20_000, heartbeatJitterFraction = 0 }`; `sendHeartbeat(): Promise<void>` guarded by `heartbeatInFlight`.
**Data Shape:** POST `/worker/heartbeat {session_id, worker_epoch}` with a SHORTER 5s timeout than the default 10s request timeout. Comment: "Default interval between heartbeat events (20s; server TTL is 60s)" — three chances per lease window.

### Decisive source
```ts
const tick = (): void => {
  void this.sendHeartbeat()
  // stopHeartbeat nulls the timer; check after the fire-and-forget send
  // but before rescheduling so close() during sendHeartbeat is honored.
  if (this.heartbeatTimer === null) return
  schedule()   // next interval ± interval*jitterFraction*(2*rand-1)
}
```
```ts
// initialize(): activity-driven liveness, separate from the timer:
// "sessionActivity's refcount-gated timer fires while an API call or tool
// is in-flight; without a write the container lease can expire mid-wait."
registerSessionActivityCallback(() => { void this.writeEvent({ type: 'keep_alive' }) })
```

**Flow:** initialize → startHeartbeat (stops any prior timer first) → every ~20s±jitter one in-flight-capped POST. close() ordering (:982-997): `closed=true` → stopHeartbeat → unregisterSessionActivityCallback → clear stream timer/buffer/accumulator → close all four uploaders.
**Invariant:** The null-check AFTER the fire-and-forget send is load-bearing: close() during an in-flight heartbeat must not be followed by a reschedule. `heartbeatInFlight` collapses overlapping ticks when a send exceeds the interval. Three DISTINCT liveness planes coexist and must not be conflated: (1) the 20s worker-lease heartbeat (this capsule); (2) sessionActivity-triggered keep_alive EVENTS while work is in-flight (container lease); (3) remoteIO's bridge-only silent keep_alive STDOUT frame every `session_keepalive_interval_v2_ms` (GrowthBook, default 120s, 0=disabled) fixing Envoy proxy idle timeout #21931. Every receiver filters keep_alive from user-visible streams (Query.ts drops it; structuredIO.processLine :344-347 silently ignores incoming keep_alive).
**Probe:** `grep -n "server TTL is 60s" src/cli/transports/ccrClient.ts` (`:32`), `grep -n "if (this.heartbeatTimer === null) return" src/cli/transports/ccrClient.ts` (`:691`), `grep -n "heartbeatInFlight" src/cli/transports/ccrClient.ts` (`:267,:707-708,:721`), `grep -n "container lease can expire mid-wait" src/cli/transports/ccrClient.ts` (`:502`). No upstream unit tests — deterministic anchors are the probe tier.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", name_pattern: "^(sendHeartbeat|stopHeartbeat|handleEpochMismatch)$", limit: 5 });
// sendHeartbeat :706-723 · stopHeartbeat :698-703 · handleEpochMismatch :669-675 (executed live pre-write;
// startHeartbeat :678-695 resolved line-exact via query-mode battery R2)
```

## Verdict
Adopt the reschedule-after-send null-check verbatim for ANY closable heartbeat loop. Adapt interval to TTL/3. Keep the liveness planes separate — collapsing the lease heartbeat with the activity keep-alive loses the "in-flight work extends the lease" property.
