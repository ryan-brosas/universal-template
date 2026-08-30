<!-- capsule-v2 -->
# Cached era verdicts — what may a gateway safely persist about a server's protocol era, and at what cost?

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** A gateway wants zero-round-trip connects via cached negotiation results — which verdict shapes are safe to store and why does the legacy one rot silently?

## Connected graph-selected seam
**Path/Symbol:** `packages/client/src/client/probeClassifier.ts`: `PriorDiscovery` (:107-111) + freshness docblock (:97-106); consumption surface `connect({ prior })`; full recipe `docs/advanced/gateway.md`.
**Signature:** `type PriorDiscovery = { kind:'modern'; discover: DiscoverResult } | { kind:'legacy' }` — the persistable subset of `ProbeVerdict`.
**Data Shape:** `'modern'` = speaks 2026-07-28+ (adopt `discover` directly: zero round trips); `'legacy'` = 2025-era initialize only (skip the probe). Freshness is the supplying host's responsibility.

### Decisive source
```ts
// Freshness is the supplying host's responsibility: a stale modern verdict
// fails loudly at the first request, but a stale legacy verdict succeeds
// silently forever (an upgraded server still answers `initialize`) — date
// cached legacy verdicts in your own storage and stop supplying them past
// your policy horizon.
```

**Flow:** first connect → probe classifies era → host stores the verdict keyed by server → later connects supply `{prior}` → modern verdicts skip negotiation entirely; legacy verdicts skip straight to initialize. Era-recovery flows key on `SdkErrorCode.EraNegotiationFailed`, which auth failures never carry (they use ClientHttpAuthentication/ClientHttpForbidden) so recovery can't persist verdicts for unauthorized exchanges.

**Invariant:** The asymmetry is the contract: stale-modern fails loudly; stale-legacy succeeds silently forever because an upgraded server still answers initialize. Therefore legacy entries MUST be dated by the storer and expire on policy. Never derive a persisted legacy verdict from an auth wall or network failure — those rows are typed errors precisely so fleet-level caches cannot poison themselves.

**Probe:** No dedicated direct test for the `prior` storage shape itself (host-side concern) — behavior covered indirectly by probe-classifier + connect tests; recorded as an in-capsule coverage caveat.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "PriorDiscovery EraNegotiationFailed connect prior", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt persist-modern-freely/date-legacy-mandatory for any multi-tenant gateway; adapt the storage key to your server identity scheme; omit the gateway doc recipe unless you operate one.
