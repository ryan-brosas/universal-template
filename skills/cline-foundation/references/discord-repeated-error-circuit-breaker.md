<!-- capsule-v2 -->
# Discord repeated-error circuit breaker — how do you keep a misbehaving bridge from spamming the platform forever?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** Turn failures post error text back to the platform — if the failure is persistent, that feedback loop itself becomes the outage. How do you break it?

## Fixed-window per-thread+message counter that escalates to connector shutdown
**Path/Symbol:** `apps/cli/src/connectors/adapters/discord.ts` turn catch (:1258-1309), constants `MAX_REPEATED_ERRORS = 3` / `ERROR_WINDOW_MS = 60_000` (:1128-1129).
**Signature:** inline in `handleTurn`'s catch; tracker `Map<`${thread.id}:${message.slice(0, 200)}`, { count; firstSeen; lastSeen }>`.
**Data Shape:** In: the thrown error + thread id. Out: one posted error message per occurrence, and a `requestStop("repeated_discord_errors")` on the third occurrence inside the window.

### Decisive source
```ts
const errorKey = `${thread.id}:${message.slice(0, 200)}`; // per-thread, per-distinct-error
const tracked = errorTracker.get(errorKey);
if (!tracked) {
    errorTracker.set(errorKey, { count: 1, firstSeen: now, lastSeen: now });
    await thread.post(`Discord bridge error: ${message}`);
} else if (now - tracked.firstSeen > ERROR_WINDOW_MS) {
    errorTracker.set(errorKey, { count: 1, firstSeen: now, lastSeen: now }); // reset
    await thread.post(`Discord bridge error: ${message}`);
} else {
    tracked.count++;
    if (tracked.count >= MAX_REPEATED_ERRORS) {
        await thread.post(`Discord bridge error (repeated ${tracked.count} times in ...): ...\n\nConnector shutting down due to repeated errors.`);
        requestStop("repeated_discord_errors");
    }
}
```

**Flow:** every turn failure is keyed by thread + first 200 chars of the error message (distinct failures do not share a counter) → first occurrence posts the error → a recurrence OUTSIDE the 60s fixed window resets the counter → the THIRD occurrence INSIDE the window posts a final shutdown notice and requests connector stop through the same `requestStop` channel used by SIGINT/SIGTERM/gateway-failure — the shutdown path still runs the full teardown (clearBindingSessionIds, abort gateway, close server, remove state file).
**Invariant:** (1) The breaker counts DISTINCT errors separately — one flaky tool call does not mask a different recurring failure, and vice versa. (2) Escalation goes through the ordinary stop channel, so cleanup is never bypassed. (3) The user-visible error text is posted at most twice before shutdown for a persistently failing turn.
**Probe:** `apps/cli/src/connectors/adapters/discord.test.ts` — no direct case for the breaker (coverage caveat: behavior anchored by the constants and the `requestStop` wiring read directly in source; the stop channel itself is test-pinned via the state-file stop paths). Companion restart behavior: `restoreDiscordThreadSubscriptions` (:689-720) re-subscribes persisted threads exactly once per thread id (test-pinned "restores persisted thread subscriptions once on startup": two bindings on one thread ⇒ subscribe called once, restored count 1).

## Get live surrounding code
**Retrieve:** *(canonical call for a connected session — NOT executed this pass)*
```ts
await mcp.codebase_memory.get_code_snippet({ project: "cline", file: "apps/cli/src/connectors/adapters/discord.ts", symbol: "handleTurn" });
```

## Verdict
Adopt the breaker shape: fixed-window per-failure counters with a small threshold that escalate through the NORMAL shutdown channel, never a bare process exit. Adapt threshold (3), window (60s), and the key slice (200 chars) to your platform's noise profile. Omit the Discord message copy. Coverage caveat: breaker itself is source-anchored only (no direct test case); the restore-once subscription behavior it pairs with IS test-pinned.
