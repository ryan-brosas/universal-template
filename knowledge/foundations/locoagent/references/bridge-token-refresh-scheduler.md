<!-- capsule-v2 -->
# Token refresh scheduler — how do proactive JWT refreshes avoid races and tight loops?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you schedule per-session token refreshes before expiry when tokens arrive in two incompatible forms (decodable JWT vs opaque with TTL) and refreshes can race cancels?

## Path/Symbol
**Path/Symbol:** `src/bridge/jwtUtils.ts` — `decodeJwtPayload` (:21-32, strips `sk-ant-si-` prefix), `decodeJwtExpiry` (:38-49), `createTokenRefreshScheduler` (:72-256); constants :52-61 (`TOKEN_REFRESH_BUFFER_MS`=5min, `FALLBACK_REFRESH_INTERVAL_MS`=30min, `MAX_REFRESH_FAILURES`=3, `REFRESH_RETRY_DELAY_MS`=60s).
**Signature:** `createTokenRefreshScheduler({getAccessToken, onRefresh(sessionId, oauthToken), label, refreshBufferMs?}) → {schedule(sessionId, jwt), scheduleFromExpiresIn(sessionId, seconds), cancel(id), cancelAll()}`.
**Data Shape:** three parallel Maps keyed by sessionId: `timers`, `failureCounts`, and `generations` (int bumped by schedule/cancel).

### Decisive source
```ts
// Generation counter per session — incremented by schedule() and cancel()
// so that in-flight async doRefresh() calls can detect when they've been
// superseded and should skip setting follow-up timers.
const generations = new Map<string, number>()
...
async function doRefresh(sessionId: string, gen: number): Promise<void> {
  let oauthToken: string | undefined
  try { oauthToken = await getAccessToken() } catch (err) { /* log */ }
  // If the session was cancelled or rescheduled while we were awaiting,
  // the generation will have changed — bail out to avoid orphaned timers.
  if (generations.get(sessionId) !== gen) { return }
```

**Flow:** `schedule()` decodes the JWT's `exp`; undecodable token ⇒ **keep existing timer** (never break a running refresh chain — REPL passes an OAuth token here). delay = `exp*1000 - now - buffer`; already-within-buffer ⇒ fire immediately. `scheduleFromExpiresIn` clamps `Math.max(expires_in*1000 - buffer, 30_000)` — the 30s floor exists because buffer>expires_in would give delay≤0 and tight-loop. On fire: re-read token post-await, generation-check, retry ≤3× on missing token (60s apart), call `onRefresh`, then **self-reschedule at the 30-min fallback** so long sessions stay authenticated past the first window.

**Invariant:** (1) The generation check must run AFTER the await inside doRefresh — checking before schedules orphan timers that clobber newer ones. (2) An undecodable token must preserve, not clear, the existing timer. (3) The follow-up fallback timer is what makes this a chain rather than a one-shot; omitting it leaves sessions dying at ~first-refresh+30min (the exact bug the comment describes). (4) Failure counter resets only on success; cap prevents infinite retry spam.

**Probe:** coverage caveat — no upstream unit tests. Deterministic pins: `grep -n "in-flight async doRefresh" src/bridge/jwtUtils.ts` (:91-93); `grep -n "Math.max(expiresInSeconds \* 1000 - refreshBufferMs, 30_000)" src/bridge/jwtUtils.ts` (:157); `grep -n "keeping existing timer" src/bridge/jwtUtils.ts` (:110); graph resolves `locoagent.src.bridge.jwtUtils.createTokenRefreshScheduler` :72-256 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "createTokenRefreshScheduler decodeJwtExpiry scheduleFromExpiresIn generations", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt whole — generation-counter invalidation + TTL-floor clamp + fallback self-reschedule is the complete recipe for any long-lived-session token ladder. Adapt `onRefresh` delivery (stdin frame for spawned children vs transport rebuild for in-process); omit nothing else.
