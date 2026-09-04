<!-- capsule-v2 -->
# Bridge API error taxonomy + OAuth retry wrapper — which HTTP statuses are fatal vs retryable, and where does token refresh hook in?

**Source:** locoagent repo `main@c01bb3f8`; Codebase Memory project `locoagent`. **Question:** How should a thin API client classify status codes into typed errors, fold 401-refresh-retry under every authed call, and keep user-visible noise down?

## handleErrorStatus + withOAuthRetry + BridgeFatalError
**Path/Symbol:** `src/bridge/bridgeApi.ts` — `BridgeFatalError` class (:56-66), `withOAuthRetry` (:106-139), `handleErrorStatus` (:454-500), `isExpiredErrorType` (:503-508), `isSuppressible403` (:516-524), `validateBridgeId` (:48-53), empty-poll log throttle (:73-74, :229-239).
**Signature:** `withOAuthRetry(fn(token) → {status,data}, context)` — single retry after successful refresh, then hand the STILL-401 response to handleErrorStatus; `new BridgeFatalError(message, status, errorType?)`.
**Data Shape:** errorType extracted from `{error:{type}}` body shape; suppressible-403 detection greps message for 'external_poll_sessions' / 'environments:manage'.

### Decisive source
```ts
case 410:
  throw new BridgeFatalError(
    detail ?? 'Remote Control session has expired. Please restart…',
    410, errorType ?? 'environment_expired')
...
export function isExpiredErrorType(errorType: string | undefined): boolean {
  if (!errorType) return false
  return errorType.includes('expired') || errorType.includes('lifetime')
}
// Poll endpoint: validateStatus s<500 means 404 ALWAYS surfaces here as
// BridgeFatalError (never an axios-shaped rejection) — that's what makes
// "poll 404 == environment gone" an unambiguous signal upstream.
```

**Flow:** every call: resolveAuth (throws login instruction if no token) → getHeaders (beta header + runner version + optional X-Trusted-Device-Token) → axios with validateStatus<500 → non-2xx ⇒ typed throw: 401 fatal (+login hint), 403 fatal (expired-flavored message iff isExpiredErrorType), 404 fatal (detail passthrough), 410 fatal w/ env-expired default type, 429 PLAIN Error ("Polling too frequently" — retryable by backoff loops), other plain Errors.
**Invariant:** (1) 401 refresh is single-shot per request; failed refresh returns the ORIGINAL 401 response so callers see a consistent fatal. (2) The fatal/retryable split is what both poll loops branch on (`instanceof BridgeFatalError` ⇒ immediate exit; otherwise budget-track) — adding statuses means updating BOTH sides of that contract. (3) validateBridgeId allowlist `[A-Za-z0-9_-]+` on EVERY path-interpolated server-provided ID before any URL build. (4) Cosmetic-permission 403s are suppressed from UI but STILL trigger teardown paths (suppressed ≠ ignorable). (5) Empty-poll debug logging throttles to first + every-100th consecutive empty poll (counter save/reset dance around the request).
**Probe:** No direct tests — deterministic pins; graph line-exact: withOAuthRetry 106-139, BridgeFatalError 56-66, validateBridgeId 48-53.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "handleErrorStatus withOAuthRetry", limit: 10 });
```

## Verdict
Adopt the taxonomy table and single-retry wrapper shape wholesale; adapt header set/beta strings. Keep validateBridgeId on every interpolated path segment — it's the traversal guard.
