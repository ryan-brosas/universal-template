<!-- capsule-v2 -->
# Retire escalation ladder — stopping someone else's daemon by force, ordered from politest to strongest

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** When a newer install must remove an old daemon, what is the force ordering, and when may discovery be cleared?

## drain → authenticated shutdown → SIGTERM at positively-alive PID → clear only on success
**Path/Symbol:** `sdk/packages/core/src/hub/daemon/index.ts:205-238` (`retireDiscoveredHub`); consumed by ensure ladder and `ensure-retire.test.ts`.
**Signature:** `retireDiscoveredHub(record: {url, authToken?, pid?}, discoveryPath) → Promise<boolean>` (true = hub actually went away).
**Data Shape:** Steps use HTTP `/drain` (+reason, off-param liftable), authenticated shutdown request, `waitForHubToRetire(url, HUB_RETIRE_TIMEOUT_MS)`, `isPidAlive(pid)`.

### Decisive source
```ts
// Graceful handover, in order of increasing force: drain (refuse new
// work), then an authenticated shutdown, then SIGTERM only as a fallback
// and only at a pid we can positively observe alive right now — a recorded
// pid may have been recycled by the OS onto an unrelated process.
await requestHubDrain(record.url, record.authToken, "retired by newer install").catch(() => false);
await requestHubShutdown(record.url, record.authToken).catch(() => false);
let retired = await waitForHubToRetire(record.url, HUB_RETIRE_TIMEOUT_MS);
if (!retired && record.pid && isPidAlive(record.pid)) {
    try { process.kill(record.pid, "SIGTERM"); } catch { /* Best-effort cleanup only. */ }
    retired = await waitForHubToRetire(record.url, HUB_RETIRE_TIMEOUT_MS);
}
// Only the successful retirement may clear discovery: clearing the record
// of a hub that survived leaves a live daemon undiscoverable, recoverable
// only through the expected-URL probe/repair path.
if (retired) { await clearHubDiscovery(discoveryPath).catch(() => undefined); }
return retired;
```

**Flow:** every step tolerates failure of the previous one (`.catch(() => false)`); SIGTERM is gated on `record.pid && isPidAlive(record.pid)` checked *at kill time* because PIDs get recycled onto unrelated processes; after each forced step the hub is re-awaited rather than assumed dead. Ownership rule: discovery clearing happens ONLY inside this function and ONLY on confirmed retirement — callers (the ensure path) must not clear it themselves (pinned by test "clears discovery for a stale record whose endpoint is gone" vs "expect(clearHubDiscovery).not.toHaveBeenCalled()" on the busy path).
**Invariant:** Never signal an unverified PID; never declare retirement without observing the endpoint gone; never leave a live daemon undiscoverable (clear ⇒ only after confirmed death). Busy hubs are deferred upward as `deferred_busy`, letting the ensure ladder attach instead of ambush.
**Probe:** `grep -cF '"retired by newer install"' sdk/packages/core/src/hub/daemon/index.ts` → 1; `grep -cF 'if (!retired && record.pid && isPidAlive(record.pid)) {' ...` → 1; `grep -cF '// Only the successful retirement may clear discovery: clearing the record' ...` → 1. Direct tests: `hub/server/hub-websocket-server.ensure-retire.test.ts` ("attaches to a busy unusable hub instead of retiring it", "retires an idle unusable hub through the shared drain-first retirement", "clears discovery for a stale record whose endpoint is gone").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "cline", query: "retireDiscoveredHub requestHubDrain waitForHubToRetire", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt force-ordering (drain→shutdown→SIGTERM-at-verified-pid) and the clear-only-on-confirmed-death ownership rule for any daemon/child-process replacement story. Adapt transport verbs, timeouts, and reason copy. Omit Cline's doctor-fix UX around it. Runner-BLOCKED here; probes green.
