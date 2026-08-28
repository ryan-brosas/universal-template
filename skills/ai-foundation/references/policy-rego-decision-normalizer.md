<!-- capsule-v2 -->
# Rego decision normalization — how do you normalize two generations of Rego output conventions into one decision type?

**Source:** Vercel AI SDK (inspo/ai) Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory project `ai` (MCP not connected this session — direct source read fallback). **Question:** policy rules written across years emit different result shapes — how does one normalizer accept them all while defaulting unknown shapes to "no opinion" instead of blocking?

## normalizeOpaDecision — two-convention decision normalizer
**Path/Symbol:** `packages/policy-opa/src/opa/normalize-opa-decision.ts:19` (`export function normalizeOpaDecision`, 56L whole); reason carrier `withReason` :51–56.

**Signature:**
```ts
function normalizeOpaDecision(result: unknown): PolicyDecision;
// accepts: { decision: 'allow'|'deny'|'requires-approval'|'not-applicable', reason?: string }
//       or { allow: boolean, reason?: string }
//       or anything else -> { type: 'not-applicable' }
```

**Data Shape:** recommended explicit form maps `allow→approved`, `deny→denied`, `requires-approval→user-approval` (deliberately WITHOUT a reason — the SDK's user-approval arm has no reason slot), `not-applicable→not-applicable`. Legacy boolean form maps `true→approved`, `false→denied`, both carrying an optional reason.

### Decisive source
```ts
if (result == null) return { type: 'not-applicable' };
if (typeof result !== 'object') return { type: 'not-applicable' };
const record = result as Record<string, unknown>;
const reason = typeof record.reason === 'string' ? record.reason : undefined;
if (typeof record.decision === 'string') {
  switch (record.decision) {
    case 'allow': return withReason('approved', reason);
    case 'deny': return withReason('denied', reason);
    case 'requires-approval': return { type: 'user-approval' };
    case 'not-applicable': return { type: 'not-applicable' };
  }
}
if (typeof record.allow === 'boolean') {
  return withReason(record.allow ? 'approved' : 'denied', reason);
}
return { type: 'not-applicable' };
```

**Flow:** engine result (any shape) → null/primitive/unrecognized → `not-applicable` → explicit `decision` string wins → legacy `allow` boolean wins → fallthrough `not-applicable`. A non-matching Rego rule (undefined decision document) therefore defaults to "no opinion" rather than blocking.

**Invariant:** unknown shapes NEVER map to a deny or an approval — the only safe default for a policy engine that didn't match is "no opinion", which lets the surrounding wrapper (`wrapMcpTools` fallback, SDK default) decide. Reason strings flow through only when actually strings; a non-string reason is dropped, never coerced.

**Probe:** `packages/policy-opa/src/opa/normalize-opa-decision.test.ts` (13 cases): explicit form ×5 (allow/deny+reason/requires-approval/not-applicable), legacy boolean ×3, fallthrough ×5 (null, undefined, `{result:'maybe'}`, string `'yes'`, number `42` all → not-applicable).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "normalizeOpaDecision requires-approval allow boolean not-applicable", limit: 10, fields: ["signature", "name", "file"] });
```
Expected rank: normalize-opa-decision.ts :19, then its test describe :4.

## Verdict
Adopt the explicit-then-legacy-then-no-opinion normalizer shape for any engine with evolving output conventions; adapt the decision vocabulary to your host's approval states; omit the Rego field names if your engine differs. Coverage caveat: none — fully test-pinned (13 cases).
