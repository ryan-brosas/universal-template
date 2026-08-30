<!-- capsule-v2 -->
# Named rate-limit policy table — how do you keep every endpoint's throttle budget isolated, named, and keyed against the right abuser?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1` (drift pass — file expanded with auth + AI + DNS policies). **Question:** How should per-endpoint rate limits be declared so keys can't collide and messages stay contract-stable?

## RATELIMIT_POLICIES: declarative records consumed by the single assert gate
**Path/Symbol:** `apps/web/lib/upstash/ratelimit-policies.ts:RATELIMIT_POLICIES` (:18-110); consumer pattern in `policy-rate-limit` capsule (`assertRateLimit`).
**Signature:** `RatelimitPolicy = { attempts: number; window: string; keyPrefix: string; message?: string | ((ctx:{retryAfter,attempts,window}) => string) }`; table `as const satisfies Record<string, RatelimitPolicy>`.
**Data Shape:** `window` is Upstash's duration grammar ("1 m", "24 h", "1 h"); keyPrefixes are namespaced `rl:<domain>:<endpoint>[:variant]`.

### Decisive source
```ts
login: {
  attempts: 5, window: "1 m", keyPrefix: "rl:auth:login",
  message: "too-many-login-attempts", // exact error code matched by the sign-in page, must stay verbatim
},
// Keyed on the target email so many accounts can't spam the same address
emailChangeRequestTarget: { attempts: 3, window: "24 h", keyPrefix: "rl:auth:email-change:target" },
aiRewardGenerate: { attempts: 10, window: "1 m", keyPrefix: "rl:ai:reward:generate" },
```

**Flow:** callers pick a NAMED policy and compose the final Redis key as `[keyPrefix, ...entityIds].join(":")` → the shared limiter asserts and throws the policy's message (or formats retry-after) on breach. The table grew two KEYING STRATEGIES worth porting: dual policies for one flow where the requester AND the target each get their own budget (`emailChangeRequest` vs `...Target`, `forwardDnsInstructions` vs `...Target`) so one actor cannot exhaust a victim's quota; and literal-string error contracts (login's message is matched verbatim by the sign-in page — a comment pins it).
**Invariant:** every distinct abuse surface gets its own keyPrefix (auth login ≠ login-link ≠ OTP send ≠ password reset) so budgets never bleed into each other; when both sides of an interaction can be attacked, there are TWO policies — actor-keyed and target-keyed. Messages that UI code string-matches are frozen contract strings. The table is `satisfies`-checked so typos in shape fail compile.
**Probe:** no direct unit test pins individual policies upstream (they're exercised through auth flows end-to-end) — coverage caveat; deterministic probe: 6th login within a minute returns exactly `"too-many-login-attempts"` while password-reset attempts remain unaffected.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "RATELIMIT_POLICIES ratelimit", limit: 6 });
// → lib.upstash.ratelimit-policies.RATELIMIT_POLICIES @ ratelimit-policies.ts 18-110
```

## Verdict
Adopt the named-policy table with namespaced key prefixes, actor/target dual keying, and frozen contract messages. Adapt windows/attempts to your threat model. Omit message functions if errors surface only as codes.
