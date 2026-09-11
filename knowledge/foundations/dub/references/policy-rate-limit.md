<!-- capsule-v2 -->
# Policy rate limiting — declarative policies + one assert gate with human retry-after

**Source:** dub AGPL-3.0-or-later (EE dirs separately licensed) `main@873edc5a9727317513c966b8d9b9171794fc89f8`; Codebase Memory `dub`. **Question:** How do you centralize rate limiting so every endpoint enforces a named policy instead of hand-rolling limits?

## assertRateLimit / RATELIMIT_POLICIES
**Path/Symbol:** `apps/web/lib/upstash/assert-rate-limit.ts:assertRateLimit` (28–67), `formatRetryAfter` (8–24); `apps/web/lib/upstash/ratelimit-policies.ts:RATELIMIT_POLICIES` (18–92); limiter factory `apps/web/lib/upstash/ratelimit.ts` (5–21).
**Signature:** `assertRateLimit({ policy: RatelimitPolicy, identifier: string | string[] }): Promise<void>` (throws). `ratelimit(requests = 10, seconds = "10 s"): Ratelimit` — Upstash sliding-window, `timeout: 1000` ms, analytics on.
**Data Shape:** `RatelimitPolicy = { attempts: number; window: "N ms|s|m|h|d"; keyPrefix: string; message?: string | ((ctx:{retryAfter,attempts,window}) => string) }`. Redis key = `[policy.keyPrefix, ...identifier].join(":")`.

### Decisive source
```ts
if (!shouldApplyRateLimit) return;                       // env kill-switch (tests/dev skip)
const key = [policy.keyPrefix, ...(Array.isArray(identifier) ? identifier : [identifier])].join(":");
const { success, reset } = await ratelimit(policy.attempts, policy.window).limit(key);
if (!success) {
  const retryAfter = formatRetryAfter(reset);            // ceil secs -> "45 seconds"/"3 minutes"/"2 hours", min 1s
  const message = typeof policy.message === "function"
    ? policy.message({ retryAfter, attempts: policy.attempts, window: policy.window })
    : policy.message ?? `Too many requests. Please try again in ${retryAfter}.`;
  throw new DubApiError({ code: "rate_limit_exceeded", message });
}
```

**Flow:** call sites pick a named policy (`RATELIMIT_POLICIES.login`, `.signupOtpSend`, … — 12 declared) and pass the dynamic identifier parts (email, ip, target address); the gate builds the namespaced key, runs the sliding window, and on failure throws the standard API error so the global error handler renders it. Some policies use a VERBATIM message string that doubles as a client-side error-code match (`login` → `"too-many-login-attemptso"` must stay exact for the sign-in page).
**Invariant:** the limiter never blocks longer than 1 s (`timeout: 1000`) — availability of the protected endpoint beats limit accuracy; the kill-switch is checked BEFORE any Redis call; keys are always prefixed by policy so different endpoints can't exhaust each other's budgets.
**Probe:** no direct unit test (policies table is data). Source-grounded probe: `search_graph` resolves `assertRateLimit`; port with your own test asserting the composed key shape and the thrown `rate_limit_exceeded` code.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "assertRateLimit RATELIMIT_POLICIES ratelimit", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the policy-table + single-gate pattern, key composition `[keyPrefix, ...ids].join(":")`, the ≤1s timeout posture, the kill-switch, and the retry-after formatter; adapt the backing store (Upstash here → any sliding-window limiter), the policy values, and verbatim-message contracts. Omit Upstash analytics. Caveat: no direct upstream test for this seam.
