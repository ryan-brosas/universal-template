<!-- capsule-v2 -->
# Attribution fingerprint scoring — weighted factors, NAT-unattributable IP exclusion, and per-link attribution windows

**Source:** LinkForty core AGPL-3.0-only `main@8919b1ecdc48f8c53340c4590b5f0eae0680abf8`; Codebase Memory `ext-core`. **Question:** How do you match an app install back to a click without ad IDs — and when must an IP match NOT count?

## calculateConfidenceScore + isAttributableIp + matchInstallToClick
**Path/Symbol:** `src/lib/fingerprint.ts:FINGERPRINT_WEIGHTS` (:33-39), `calculateConfidenceScore` (:182-255), `isAttributableIp` (:115-140), `matchInstallToClick` (:263-346).
**Signature:** `function calculateConfidenceScore(f1: FingerprintData, f2: FingerprintData): { score: number; matchedFactors: string[] }`; weights IP=40 UA=30 TZ=10 LANG=10 SCREEN=10; `CONFIDENCE_THRESHOLD = 70`, `DEFAULT_ATTRIBUTION_WINDOW_HOURS = 168`.
**Data Shape:** Factors are compared only when BOTH sides carry the field (absent ≠ mismatch); matched factor names accumulate into `matchedFactors` (`ip`/`user_agent`/`timezone`/`language`/`screen`) persisted on install rows for attribution-quality measurement.

### Decisive source
```ts
// fingerprint.ts:189-205 — the NAT guard a porter will get wrong:
// Only count IPs that actually identify a device — shared/NAT ranges (CGNAT,
// RFC1918, etc.) are skipped so unrelated users behind the same NAT can't match.
if (fp1.ipAddress && fp2.ipAddress &&
    isAttributableIp(fp1.ipAddress) && isAttributableIp(fp2.ipAddress)) {
  const ip1 = normalizeIP(fp1.ipAddress); // /24 for v4 (first 3 octets), first 4 groups v6
  if (ip1 === ip2) { score += FINGERPRINT_WEIGHTS.IP_ADDRESS; matchedFactors.push('ip'); }
}
```

**Flow:** candidate clicks = last 1000 within hard 90-day ceiling JOINed to device_fingerprints and links → per-row check against THAT link's `attribution_window_hours` (default 168h) → score each → keep best strictly-greater-than-current-high above threshold → `recordInstallEvent` stores attribution_method `'fingerprint'|'none'`, retrieves deep-link payload from the matched link, fires install webhooks only on attributed installs. `isAttributableIp` excludes CGNAT 100.64/10 ("the Marriage365 case" in tests), RFC1918, loopback, link-local, benchmarking, IPv6 ULA/link-local/unspecified, after unwrapping `::ffff:` mapped v4; language matches on first-2-chars lowercased (`en-US` ≍ `en-GB`); UA normalizes to `platform|browser` lowercase.
**Invariant:** An IP in a shared range contributes ZERO points even though both sides "match" — without this guard every office-NAT user cross-attributes; matching requires ≥70 so ip+ua alone (70) passes but ua+tz+lang+screen (60) does not.
**Probe:** `bash -c "grep -c 'NON_ATTRIBUTABLE_V4' src/lib/fingerprint.ts"` → 2 (:97 declaration + :124 use — count LINES not occurrences); direct tests `src/lib/fingerprint.test.ts`: it('matches IP within the same /24 subnet...'), it('rejects CGNAT (100.64.0.0/10) — the Marriage365 case'), it('matches language by first two characters').

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-core", query: "calculateConfidenceScore isAttributableIp attribution window", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the weight table + threshold + NAT-exclusion + per-link-window structure wholesale for probabilistic attribution; adapt weights/thresholds to your signal quality; omit geoip-derived fields you cannot collect — but never let shared-range IPs contribute match score.
