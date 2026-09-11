<!-- capsule-v2 -->
# Debug simulate endpoint — redirect-decision replay without side effects, per-dimension targeting detail

**Source:** LinkForty core AGPL-3.0-only `main@8919b1ecdc48f8c53340c4590b5f0eae0680abf8`; Codebase Memory `ext-core`. **Question:** How do you expose "what WOULD happen for this click" without recording clicks or mutating anything?

## POST /api/debug/simulate + reference fixtures
**Path/Symbol:** `src/routes/debug.ts:simulateRequestSchema` (:10-18), handler (:32-181), UA/country/language fixture endpoints (:187-299).
**Signature:** Body `{ linkId: uuid, userId?, deviceType?: 'ios'|'android'|'web', userAgent?, country? (2-letter), language?, ipAddress? }` → response `{ simulation, input, detection, targeting, redirect, warnings[] }`.
**Data Shape:** Device resolution precedence: explicit deviceType > detectDevice(userAgent) > 'web'; `detectionMethod` reports which tier fired; simulated defaults US/en when query fields absent.

### Decisive source
```ts
// debug.ts:160-179 — decision + honest warning list:
targeting: { hasRules, rules, matched, details },
redirect: { wouldRedirect: link.is_active && targetingMatched,
            finalUrl: targetingMatched ? finalUrl : null,
            redirectReason: ..., utmParametersAdded: ... },
warnings: [
  ...(!link.is_active ? ['Link is inactive - would return 404'] : []),
  ...(link.expires_at && new Date(link.expires_at) < new Date() ? ['Link has expired - would return 404'] : []),
  ...(!targetingMatched ? ['Targeting rules not matched - would return 404'] : []),
],
```

**Flow:** fetch link (ownership-scoped when userId provided) → resolve device tier → evaluate the three rule dimensions collecting PER-DIMENSION booleans (countryMatch/deviceMatch/languageMatch, null = no rule) → build finalUrl with UTM params → return full decision object with warnings instead of executing any redirect/insert. Language matching here uses PREFIX startsWith — looser than redirect.ts exact-subtag equality (deliberate diagnostic twin; targeting capsule records the divergence).
**Invariant:** A debug/simulate surface must be read-only (no click rows, no fingerprints, no webhooks); its verdict must enumerate WHY a 404 would occur, not just whether.
**Probe:** `bash -c "grep -cF \"would return 404\" src/routes/debug.ts"` → 3 (:174/:176/:178); direct tests: none target debug.ts — recorded honest caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-core", query: "simulate device targeting debug", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt read-only decision-replay endpoints for link debugging with per-dimension match detail; adapt dimensions; omit the fixture endpoints in production builds — and reconcile the language-match divergence before trusting simulate as an oracle for exact redirect behavior.
