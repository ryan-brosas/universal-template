<!-- capsule-v2 -->
# Quota snapshot parsing — how do you turn untrusted provider quota JSON into a worst-case health signal that never overestimates an account?

**Source:** pi-multi-pass MIT-declared per package.json (no LICENSE file at pin; citations-only) `main@b9d9d1d7a09252a19ec79868517d49d4f07c4760`; Codebase Memory `pi-multi-pass`. **Question:** How can provider quota responses of unknown shape feed routing decisions without a malformed payload ever throwing or making a drained account look healthy?

## Parse -> collapse -> worst-wins merge -> fold -> band, all pure and total
**Path/Symbol:** `extensions/multi-sub.ts`: `normalizeGoogleRemainingPercent` (811-814), `parseIsoTimestampSeconds` (456-461), `getRecord` (362-365), `getGoogleGeminiModelLabel` (879-885), `updateGoogleQuotaModel` (830-856), `buildGoogleQuotaSnapshot` (858-877), `parseGoogleGeminiQuotaSnapshot` (887-909), `parseGoogleAntigravityQuotaSnapshot` (911-942), `classifyGoogleQuotaKind` (944-956); types `QuotaStatusKind` (271), `GoogleQuotaModelSnapshot` (339-343), `GoogleQuotaAccountSnapshot` (345-350).
**Signature:** `function updateGoogleQuotaModel(modelsByName: Map<string, GoogleQuotaModelSnapshot>, model: string, remainingPercent: number | undefined, resetAt: number | undefined): void`; `function classifyGoogleQuotaKind(snapshot: GoogleQuotaAccountSnapshot): { kind: QuotaStatusKind; score: number }`.
**Data Shape:** fraction 0..1 -> integer percent clamped [0,100] or undefined; ISO string -> floor(epoch seconds) or undefined; account snapshot = { endpoint, projectId?, models: [{model, remainingPercent?, resetAt?}], worstRemainingPercent? }; bands ready/watch/low/blocked/error/missing-auth.

### Decisive source
```ts
// worst-wins merge kernel: defined beats undefined, SMALLER percent wins, EARLIEST reset wins
if (remainingPercent !== undefined) {
  if (existing.remainingPercent === undefined || remainingPercent < existing.remainingPercent) {
    next = { ...next, remainingPercent };
  }
}
if (resetAt !== undefined) {
  if (next.resetAt === undefined || resetAt < next.resetAt) {
    next = { ...next, resetAt };
  }
}
if (next !== existing) modelsByName.set(model, next);
// parsers skip entries with no signal at all, then fold min across models:
if (remainingPercent === undefined && resetAt === undefined) continue;
const worstRemainingPercent = remainingPercents.length > 0 ? Math.min(...remainingPercents) : undefined;
// banding at the bottleneck value; no data is "error", never an exception
if (bottleneck <= 5) return { kind: "blocked", score: bottleneck };
if (bottleneck <= 15) return { kind: "low", score: bottleneck };
if (bottleneck <= 30) return { kind: "watch", score: bottleneck };
return { kind: "ready", score: bottleneck };
```

**Flow:** defensive field guards (`getRecord` rejects null/array/non-object; non-finite numbers and unparseable dates map to undefined, never throw) -> variant collapse (Gemini buckets squash onto coarse labels via contains-"pro"/"flash"; Antigravity resolves displayName > model > key and drops `isInternal === true` plus hidden names checked against BOTH key and resolved display name; entries missing BOTH percent and reset are skipped) -> per-label worst-wins merge with immutable write-back only on change -> account fold to `worstRemainingPercent = Math.min` over models (undefined when none report) -> banding at fixed thresholds. Consumer boundary `checkGoogleQuotaAccount` (1110-1193) wraps this in the typed result taxonomy: missing-auth score 0 when the oauth entry or BOTH access+refresh tokens are absent; kind "error" ("no model quota data returned") when the snapshot has empty models or undefined worst; AbortSignal errors RETHROWN while every other transport failure degrades to kind "error" score 0; `fetchSnapshot` is an INJECTED parameter so tests stub transport. `compareQuotaResults` (518-538) fixes the total order ready<watch<low<blocked<error<missing-auth, then higher score, then displayName localeCompare.
**Invariant:** untrusted upstream JSON can never throw NOR overestimate health — every field independently validated, aggregation deliberately pessimistic (min remaining, earliest reset), so failover decisions err toward safety; empty/garbage payloads yield an empty snapshot classified as "error", not a crash.
**Probe:** `node tests/subscription-limits-check.mjs` (pins min-wins merge: two Pro buckets 0.82+0.61 -> 61; hidden/internal filtering; threshold boundaries 80/25/10/3/undefined; Codex twin matches windows by duration +/-120s so reversed primary/secondary order still classifies). Green at b9d9d1d7a092.
**Coverage note:** extensions/multi-sub.ts and tests/subscription-limits-check.mjs indexed FULL, no_recorded_issue, generation match 2026-08-24T14:18:05Z; cited ranges read directly from source at the pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-multi-pass", query: "parseGoogleGeminiQuotaSnapshot updateGoogleQuotaModel classifyGoogleQuotaKind", limit: 3 });
```

## Verdict
Adopt the five-stage pure ladder (guard -> collapse -> worst-wins merge -> min-fold -> band) plus the typed result taxonomy and injected fetch boundary for any provider-health polling. Adapt endpoint/auth specifics and label vocabularies to your providers. Omit provider-specific quota scrapers you have not verified against live APIs (leaf boundary).
