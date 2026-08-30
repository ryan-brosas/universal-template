<!-- capsule-v2 -->
# Link safety three-state gate — allow / warn / block, and why block must look exactly like an unknown code

**Source:** LinkForty core AGPL-3.0-only `main@8919b1ecdc48f8c53340c4590b5f0eae0680abf8`; Codebase Memory `ext-core`. **Question:** What decides whether a found link resolves, warns, or disappears — and what must a porter never change about the block response?

## evaluateLinkSafety ordering + response-indistinguishability
**Path/Symbol:** `src/lib/link-safety.ts:evaluateLinkSafety` (:39-44); consumed at `src/routes/redirect.ts:270-292` and `src/routes/sdk.ts:538-546`.
**Signature:** `function evaluateLinkSafety(input: { isActive?: boolean | null; warnAt?: Date | string | null; ownerSuspendedAt?: Date | string | null }): 'allow' | 'warn' | 'block'`.
**Data Shape:** All three inputs nullable/optional; absent `isActive` = active (existing rows unaffected); `ownerSuspendedAt` optional because the owning column lives in downstream deployments, not this package's schema.

### Decisive source
```ts
// link-safety.ts:39-44 — ORDER MATTERS: suspension and inactivity beat warn.
if (input.ownerSuspendedAt != null) return 'block';
if (input.isActive === false) return 'block';
if (input.warnAt != null) return 'warn';
return 'allow';

// redirect.ts:276-278
if (safety === 'block') {
  // Same response as an unknown code — see evaluateLinkSafety for why.
  return reply.status(404).send({ error: 'Link not found' });
}
```

**Flow:** SQL already filters `is_active = true` + unexpired; the gate runs AFTER the cache read so it covers cached rows too; `warn` serves the interstitial (`generateWarningLinkHTML`) with NO click recorded (a warning view is not a click — recording it would inflate owner analytics); SDK resolve treats `warn` as resolvable (an app cannot render a browser interstitial; warn is suspicion, not confirmation) but enforces `block` identically.
**Invariant:** `block` MUST return byte-identical response to an unknown short code (404 `{error:'Link not found'}`) on EVERY resolving path — a distinct "this link was disabled" body would confirm to a prober that the code was real and that its owner is restricted; owner-suspension outranks warn.
**Probe:** per-file line counts (multi-file grep prints per-file lines): `bash -c "grep -cF 'same response as an unknown short code' src/lib/link-safety.ts"` → 1 (:14); `bash -c "grep -cF 'Same response as an unknown code' src/routes/redirect.ts"` → 1 (:277); `bash -c "grep -cF 'Same response as an unknown short code' src/routes/sdk.ts"` → 1 (:544); direct tests `src/lib/link-safety.test.ts` describe('evaluateLinkSafety') incl. "prefers block over warn" + `src/routes/redirect.safety.test.ts` it('gives a restricted owner the SAME response as an unknown code, leaking nothing').

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-core", query: "evaluateLinkSafety warn block interstitial", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-state enum, the precedence order (suspension > inactive > warn), post-cache-read evaluation, and response indistinguishability under block; adapt which signals feed each state; omit warn-state click suppression only if your analytics defines warning views as billable events (LinkForty says they are not).
