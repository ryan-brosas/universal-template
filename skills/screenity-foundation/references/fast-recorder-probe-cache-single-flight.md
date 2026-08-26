<!-- capsule-v2 -->
# Probe cache + single-flight — how do you cache a capability probe so failures never outlive a driver fix?

**Source:** screenity GPL-3.0 `master@e10e375fafa1680de99ca6db36536dd4a1f4f7d4`; Codebase Memory `screenity`. **Question:** How should an expensive encoder-capability probe be cached and coalesced so concurrent callers share one probe, success persists across restarts, and failure is retried within a minute?

## Two-tier cache with in-flight coalescing
**Path/Symbol:** `src/media/fastRecorderGate.ts:428-450` (`probeFastRecorderSupport`, `prewarmFastRecorderProbe`), `:401-426` (`tryReadCachedProbe`), `:381-399` (TTLs, `_probeInFlight`, `invalidateCachedProbe`).
**Signature:** `probeFastRecorderSupport(): Promise<FastRecorderProbeResult>`; `prewarmFastRecorderProbe(): void`.
**Data Shape:** memory slot `_probeInMemory/_probeInMemoryAt/_probeInFlight`; storage key `fastRecorderProbe` whose `details.userAgent` + `details.gateVersion` form the cache key; TTLs: success 7 days, failure 60 seconds in memory only.

### Decisive source
```ts
export const probeFastRecorderSupport = async (): Promise<FastRecorderProbeResult> => {
  const cached = await tryReadCachedProbe();
  if (cached) return cached;
  if (_probeInFlight) return _probeInFlight;
  _probeInFlight = _probeFastRecorderSupportUncached().finally(() => {
    _probeInFlight = null;
  });
  const result = await _probeInFlight;
  // Cache both success and failure in memory. Success rides the long
  // TTL via storage; failure rides the short in-memory TTL only so a
  // hardware/driver fix is rediscovered within a minute.
  _probeInMemory = result;
  _probeInMemoryAt = Date.now();
  return result;
};
```
Storage read validates the key triple before trusting:
```ts
if (
  cached && cached.ok === true &&
  typeof cached.at === "number" &&
  Date.now() - cached.at < PROBE_CACHE_TTL_MS &&
  cached.details?.userAgent === ua &&
  cached.details?.gateVersion === GATE_VERSION
) { ... }
```

**Flow:** memory hit → storage hit (ok-only, UA+version matched, fresh) → join in-flight promise → run uncached probe → cache result (success also persisted to storage by the uncached path; failure only to `fastRecorderProbeLastFailure`, never into the long-TTL slot).
**Invariant:** ok=false must NEVER be written to the persistent probe key (a stale failure would ban the fast path until TTL even after the driver recovers); cache identity includes browser UA AND gate-version string (`ladder-v1`) so upgrades invalidate; `invalidateCachedProbe()` clears both tiers and is invoked by real (`markFastRecorderFailure`) failures.
**Probe:** deterministic anchors: grep for `hardware/driver fix is rediscovered within a minute` (:437-438), `ok=false isn't cached so a driver recovery re-probes immediately` (:381-382 comment), `Safe to call multiple times; coalesces via _probeInFlight` (:444-446). Byte-exact at HEAD.

## Get live surrounding code
**Retrieve:**
```
search_graph(project="screenity", file_pattern="*fastRecorderGate*", query="probe cache invalidate prewarm")
→ observed 41 nodes total in module; decisive rows: tryReadCachedProbe :401-426,
  probeFastRecorderSupport :428-442, prewarmFastRecorderProbe :447-450, invalidateCachedProbe :391-399.
```

## Verdict
Adopt the asymmetric-TTL two-tier cache and single-flight coalescing wholesale. Adapt the storage medium and the cache-key fields (UA+version is the minimum viable identity). Omit the debug-log URL-param gating.
