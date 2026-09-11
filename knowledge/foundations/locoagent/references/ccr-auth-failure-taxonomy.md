<!-- capsule-v2 -->
# CCR auth-failure taxonomy — how do you distinguish "my token is dead" from "the auth server is having a bad day" before exiting a worker?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** When every write returns 401/403, what decision ladder separates deterministic death (expired JWT) from ride-out-able server blips, and how does 429 feed the retry machine?

## Token-reality split with a threshold ride-out
**Path/Symbol:** `src/cli/transports/ccrClient.ts`: `MAX_CONSECUTIVE_AUTH_FAILURES`/:62-68, `alwaysValidStatus`/:44-47, `request`/:556-642 (auth ladder :586-614, Retry-After :623-629), `handleEpochMismatch`/:669-675.
**Signature:** `request(method, path, body, label, {timeout=10_000}): Promise<{ok:true} | {ok:false; retryAfterMs?: number}>`; counter `consecutiveAuthFailures` reset by ANY 2xx (:582-585).
**Data Shape:** axios `validateStatus: alwaysValidStatus` — EVERY status is handled explicitly in code (hoisted to avoid per-request closure allocation); 429 `Retry-After` parsed as integer SECONDS.

### Decisive source
```ts
if (response.status === 401 || response.status === 403) {
  // A 401 with an expired JWT is deterministic — no retry will
  // ever succeed. Check the token's own exp before burning
  // wall-clock on the threshold loop.
  const tok = getSessionIngressAuthToken()
  const exp = tok ? decodeJwtExpiry(tok) : null
  if (exp !== null && exp * 1000 < Date.now()) {
    logForDebugging(`... session_token expired ... no refresh was delivered, exiting`)
    this.onEpochMismatch()                       // immediate exit
  }
  // Token looks valid but server says 401 — possible server-side
  // blip (userauth down, KMS hiccup). Count toward threshold.
  this.consecutiveAuthFailures++
  if (this.consecutiveAuthFailures >= MAX_CONSECUTIVE_AUTH_FAILURES) {
    this.onEpochMismatch()                       // 10 × 20s ≈ 200s ride-out
  }
}
```
```ts
if (response.status === 429) {
  const seconds = parseInt(response.headers?.['retry-after'], 10)
  if (!isNaN(seconds) && seconds >= 0)
    return { ok: false, retryAfterMs: seconds * 1000 }  // → uploader clamp+jitter
}
```

**Flow:** empty auth headers ⇒ `{ok:false}` immediately; non-2xx ⇒ 409 epoch-mismatch branch (never returns) / 401+403 token-reality ladder / 429 hint extraction / warn-log everything else; thrown transport errors are caught and normalized to `{ok:false}` so callers (uploader send()) wrap them in RetryableError.
**Invariant:** Expired-JWT 401 exits IMMEDIATELY — spending the 200s threshold on a deterministically dead token wastes a lease window. The uncertain case (token's exp in the future but server rejects) rides out up to MAX=10 consecutive failures (~200s at the 20s heartbeat cadence: userauth down, KMS hiccup, clock skew); ANY success resets the counter. 409 is fatal-by-supersession, not auth. retryAfterMs flows into SerialBatchEventUploader.retryDelay's clamp+jitter (see serial-batch-uploader-retry-machine) so a misbehaving server can neither hot-loop nor stall the client. Never throw from request() for ordinary failures — the return-union keeps uploader semantics uniform.
**Probe:** `grep -n "MAX_CONSECUTIVE_AUTH_FAILURES = 10" src/cli/transports/ccrClient.ts` (`:68`), `grep -n "deterministic — no retry" src/cli/transports/ccrClient.ts` (`:590` comment), `grep -n "retryAfterMs: seconds \* 1000" src/cli/transports/ccrClient.ts` (`:627`), `grep -n "function alwaysValidStatus" src/cli/transports/ccrClient.ts` (`:45`). No upstream unit tests — deterministic anchors are the probe tier.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "authenticated request expired token consecutive auth failures retry-after epoch mismatch 409", limit: 5 });
// request :556-642 + getWithRetry :905-958 + handleEpochMismatch :669-675 (executed live pre-write)
```

## Verdict
Adopt the two-question ladder ("is MY credential provably dead? else how many consecutive rejections?") for any lease-holding worker. Adapt the threshold to your heartbeat cadence. Omit Retry-After parsing only if your retry layer already consumes server hints upstream.
