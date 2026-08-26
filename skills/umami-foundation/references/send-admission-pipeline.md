<!-- capsule-v2 -->
# Send-route admission pipeline — what is the exact validation order that turns an untrusted POST into a stored analytics event?

**Source:** umami v3.3.1 / MIT @ master`ca661c70`; Codebase Memory `ext-umami`. **Question:** In what order are schema, website, bots, blocked IPs, and identity handled in the collect endpoint?

## send-admission-pipeline
**Path/Symbol:** `src/app/api/send/route.ts:POST :85-361` — zod schema :29-84 with `safeStringParam` CSV-formula guard :22-27; bot check :135-137; IP block :140-142; event URL/UTM/click-id parsing :199-262; identify branch :316-342.
**Signature:** `POST /api/send` `{type: 'event'|'identify'|'performance', payload}`; exactly-one-of `website|link|pixel` enforced by `.refine(count === 1)`.
**Data Shape:** performance metrics individually bounded (`lcp/inp/fcp/ttfb ≤ 60000`, `cls ≤ 100`) — numeric sanity at the SCHEMA layer.

### Decisive source
```ts
if (!process.env.DISABLE_BOT_CHECK && isbot(userAgent)) {
  return json({ beep: 'boop' });        // bots get a 200 joke, NOT an error signal
}
if (hasBlockedIp(ip)) return forbidden();
...
if (referrerDomain === eventDomain) referrerDomain = undefined;   // never save self-referrals
// identify: link write is best-effort, session-data write must not be blocked by it
try { await Promise.all([saveSessionLink(...), updateSession(...)]); sessionLinkId = newLinkId; }
catch (e) { console.error('Failed to save session link:', e); }
```

**Flow:** parseRequest(skipAuth) → cache token fast-path → website existence (unless cached) → client info → bot → blocklist → derive ids → per-type branch (event: URL canonicalization + UTM/click-id extraction + trailing-slash policy + self-referral suppression; identify: dedup via `hash(sessionId, id)` link token carried IN the cache token so repeat identifies skip writes) → mint new cache token.
**Invariant:** bots receive a NORMAL success-shaped response so naive client retries don't amplify; the identify link-dedup token rides the cache JWT (stateless dedup across requests). URL parsing uses `https://<hostname-or-localhost>` as base so path-only payloads still parse — never let `new URL()` throw into a 500.
**Probe:** structural pins: `grep -n "beep: 'boop'" src/app/api/send/route.ts` → :136; `grep -n "FORMULA_TRIGGER_RE" src/app/api/send/route.ts | head -1` → :22.
**Probe:** `grep -c "utm_source\|gclid" src/app/api/send/route.ts` → ≥2 lines.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "ext-umami", query: "saveEvent isbot hasBlockedIp utm gclid", limit: 10 });
```
**(Retrieve:)**

## Verdict
Adopt the ordered admission ladder (schema→identity→bot→blocklist→derive→branch→respond-with-token) for any public telemetry ingest; adapt bounds and joke-response policy; keep formula-injection guards if data ever reaches CSV export.
