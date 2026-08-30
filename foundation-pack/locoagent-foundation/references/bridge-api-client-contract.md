<!-- capsule-v2 -->
# Bridge API client — how do 401 refresh, ID validation, and fatal-vs-transient classification compose?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How should a poll/heartbeat HTTP client distinguish retryable from terminal failures and keep server-supplied IDs out of URL paths?

## Path/Symbol
**Path/Symbol:** `src/bridge/bridgeApi.ts` — `validateBridgeId` (:48-53, `/^[a-zA-Z0-9_-]+$/`), `BridgeFatalError` (:56-66), `createBridgeApiClient` (:68-452), `withOAuthRetry` (:106-139), `handleErrorStatus` (:454-500), `isExpiredErrorType` (:503-508), `isSuppressible403` (:516-524), `extractErrorTypeFromData` (:526-539); empty-poll log throttle :73-74 (log first then every 100th).
**Signature:** `withOAuthRetry(fn(token)→{status,data}, context)` — ONE refresh+retry on 401; `pollForWork(envId, secret, signal?, reclaimOlderThanMs?) → WorkResponse | null`.
**Data Shape:** deps injection: `onAuth401?` (absent for env-var-token daemon callers — their tokens can't refresh so 401 goes straight to BridgeFatalError), `getTrustedDeviceToken?` → `X-Trusted-Device-Token` header.

### Decisive source
```ts
function handleErrorStatus(status: number, data: unknown, context: string): void {
  if (status === 200 || status === 204) return
  const detail = extractErrorDetail(data)
  const errorType = extractErrorTypeFromData(data)
  switch (status) {
    case 401: throw new BridgeFatalError(`...${BRIDGE_LOGIN_INSTRUCTION}`, 401, errorType)
    case 403: throw new BridgeFatalError(
      isExpiredErrorType(errorType)
        ? 'Remote Control session has expired...'
        : `${context}: Access denied (403)...`, 403, errorType)
    ...
    case 429: throw new Error(`${context}: Rate limited (429). Polling too frequently.`)
```

**Flow:** every path-interpolated server ID passes validateBridgeId first (`../../admin` and slash-bearing IDs throw before axios sees them). Auth ladder: resolveAuth throws the login instruction when tokenless → request → on 401 attempt injected refresh once → retry once → if still 401, RETURN the response so handleErrorStatus converts it to BridgeFatalError. Classification contract: **BridgeFatalError = never retry** (401 auth, 403 permission/expiry, 404 gone, 410 expired-with-type-default); plain Error = retryable (429 rate-limit, 5xx via validateStatus<500 passthrough + network). `errorType.includes('expired'|'lifetime')` upgrades generic messages to expiry UX. Heartbeat uses SessionIngressAuth JWT (no DB hit); poll/ack use environment secret.

**Invariant:** (1) The 401-retry must RETURN the failed response rather than throwing, so classification happens in exactly one place. (2) Fatal-vs-transient is carried by the error CLASS, not status inspection at each catch site — catch blocks branch on `instanceof BridgeFatalError` only. (3) Suppressible-403 (scope gaps like `external_poll_sessions`, missing `environments:manage`) is message-substring matched deliberately — cosmetic errors must vanish without masking real permission failures. (4) Empty-poll success logs would flood at 2s cadence; throttle by counter with reset-on-work.

**Probe:** coverage caveat — no upstream unit tests. Deterministic pins: `grep -n "SAFE_ID_PATTERN" src/bridge/bridgeApi.ts` (:41); `grep -n "errorType.includes('expired') || errorType.includes('lifetime')" src/bridge/bridgeApi.ts` (:507); `grep -n "EMPTY_POLL_LOG_INTERVAL = 100" src/bridge/bridgeApi.ts` (:74); graph resolves `locoagent.src.bridge.bridgeApi.validateBridgeId` :48-53 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "withOAuthRetry BridgeFatalError handleErrorStatus validateBridgeId isSuppressible403", limit: 6, fields: ["signature","name","file"] });
```

## Verdict
Adopt the client skeleton wholesale: typed-fatal errors + single-site classification + ID validation + one-shot 401 refresh transfer to any job-polling client. Adapt status→message copy; omit trusted-device header if your server has no elevated tier.
