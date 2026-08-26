<!-- capsule-v2 -->
# Bridge debug redaction — secret-pattern scrubbing before any log line leaves the process

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you log full request/response bodies for forensics while guaranteeing session tokens never appear in them?

## Path/Symbol
**Path/Symbol:** `src/bridge/debugUtils.ts` — SECRET_FIELD_NAMES (:11-17), pattern compile (:19-22), REDACT_MIN_LENGTH=16 (:24), `redactSecrets` (:26-34, prefix8...suffix4 keep), DEBUG_MSG_LIMIT=2000 (:9), `debugTruncate` (:37-43), `debugBody` (:46-53, redact-then-truncate), axios error detail extractors (:60-121), `logBridgeSkip` centralizing the analytics cast (:128-141).
**Signature:** `debugBody(data: unknown): string` — every bridgeApi request/response debug line goes through it.
**Data Shape:** regex `"(" + fields.join('|') + ")"\s*:\s*"([^"]*)"` over JSON.stringify output; values <16 chars fully `[REDACTED]`, longer ones show first-8…last-4.

### Decisive source
```ts
const REDACT_MIN_LENGTH = 16
export function redactSecrets(s: string): string {
  return s.replace(SECRET_PATTERN, (_match, field: string, value: string) => {
    if (value.length < REDACT_MIN_LENGTH) {
      return `"${field}":"[REDACTED]"`
    }
    const redacted = `${value.slice(0, 8)}...${value.slice(-4)}`
    return `"${field}":"${redacted}"`
  })
}
...
export function debugBody(data: unknown): string {
  const raw = typeof data === 'string' ? data : jsonStringify(data)
  const s = redactSecrets(raw)   // redact BEFORE truncate
  if (s.length <= DEBUG_MSG_LIMIT) return s
  return s.slice(0, DEBUG_MSG_LIMIT) + `... (${s.length} chars)`
}
```

**Flow:** field-name allowlist (`session_ingress_token`, `environment_secret`, `access_token`, `secret`, `token`) matches the exact keys the bridge protocol uses; scrubbing happens on the serialized STRING so nested structures need no walking. Order matters: redact first, then truncate to 2000 chars — truncating first can cut a secret in half and leave the unredacted prefix. The 16-char floor keeps short non-secrets readable (e.g. `"state":"idle"` would survive anyway since it's not a listed key, but a 12-char test token gets fully redacted rather than leaking via the prefix window). Skip telemetry funnels through `logBridgeSkip` so the AnalyticsMetadata cast lives in one audited place.

**Invariant:** (1) Redaction precedes size truncation — reversed order defeats it. (2) The allowlist must cover every credential field your protocol adds; new secret fields are added to the ARRAY, not call sites. (3) Prefix/suffix retention is a debugging affordance that presumes values ≥16 chars provide no brute-force surface in logs — tighten the floor if your tokens are shorter. (4) All body logging flows through ONE function; ad-hoc jsonStringify in callers is the failure mode this design forbids.

**Probe:** coverage caveat — no upstream unit tests. Deterministic pins: `grep -n "REDACT_MIN_LENGTH = 16" src/bridge/debugUtils.ts` (:24); `grep -n "redactSecrets(raw)" src/bridge/debugUtils.ts` (:48); `grep -n "SECRET_FIELD_NAMES = \[" src/bridge/debugUtils.ts` (:11); graph resolves `locoagent.src.bridge.debugUtils.redactSecrets` :26-34 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "redactSecrets debugBody debugTruncate extractErrorDetail logBridgeSkip", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt whole — ~50 lines, directly portable, and the redact-before-truncate ordering is the part porters get wrong. Extend the field list per protocol; omit nothing else.
