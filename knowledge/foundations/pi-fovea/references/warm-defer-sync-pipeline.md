<!-- capsule-v2 -->
# Warm/defer sync pipeline — how does proactive context never block the send path?

**Source:** pi-fovea MIT `DETACHED@217a103`; Codebase Memory `pi-fovea`. **Question:** Sync must run before agent start and after every turn, but Enter-key responsiveness is sacred and re-extraction under the UI is a hang — what moves to the background and what stays inline?

## Edit-time warm + TTL probe on send + turn_end backstop
**Path/Symbol:** `src/core/sync.ts:warmSync/warmCache` (:163-233), defer branch in `sync()` (:308-329, :408-412); hook wiring `src/index.ts` (WARM_DEBOUNCE_MS=250 :263-277, before_agent_start probe:"defer" :301-333, turn_end probe:"cheap" :335-370).
**Signature:** `warmSync(root, {files, budget}, state?): Promise<void>` — never advances the baseline, never reports, never throws; `sync(..., opts?: {probe: "cheap"|"full"|"defer"})`.
**Data Shape:** `WarmCompute = {version, filesKey (sorted changed set), snapshot, warmedFiles, warmedMass, warmReasons, warmedNodes}` cached per root (≤ ROOT_CACHE_LIMIT); a hit requires BOTH version and filesKey match.

### Decisive source
```ts
// The blocking `sync` call on the user-perceived send path recomputes
// extraction, graph assembly, the baseline fingerprint, and the impact
// cascade whenever the repo drifted. warmSync runs those heavyweight
// ingredients eagerly as soon as edits land (tool_execution_end), keyed by
// state version + changed-file set, so the same drift's sync call reuses
// them and stays verdict-only.
// Send path (probe:"defer"): nothing materialized since baseline →
//   TTL-bounded porcelain probe only; a hit DEFERS to turn_end instead of
//   paying re-extraction while the UI waits. A prepared warm verdict RENDERS.
} else if (opts?.probe === "defer") {
  // No prepared verdict and real drift on the send path: never run the
  // impact cascade under the TUI's finger. Leave the baseline UNTOUCHED so
  // turn_end's full sync (the cheap backstop) reports and steers it.
  return { structural: true, red: false, tokens: 0, details: {..., deferred: true } };
}
```

**Flow:** edit/write tool lands → 250 ms debounced `warmSync` precomputes fingerprint + impact against an immutable state snapshot → user hits Enter → before_agent_start runs defer-mode: pure conversation = ~0 ms; out-of-band drift caught by the 1.2 s-TTL git probe → deferred; prepared warm → verdict rendered immediately ("respond to the Enter key, never block on it"). turn_end always full-syncs as the correctness backstop; session_start kicks background indexing + pre-establishes the first baseline so even THAT cost leaves the send path. Warm embeds focus detail from the EXACT state the warm built (`ensured` param) — no double probe/rebuild.
**Invariant:** A stale warm (more drift landed) falls through to inline compute — version+filesKey keying makes optimistic caching safe; the warm NEVER advances the baseline (only verdict rendering adopts it); warm output equals inline output bit-for-bit on the same drift (masses rounded to 6dp for payload identity); every fire-and-forget promise carries a rejection handler (headless sessions must not leak unhandled rejections).
**Probe:** `tests/sync.test.ts` — "precomputes ingredients so the blocking sync reuses them"; "warm path equals the inline compute on the same drift" (text equality asserted); "stale warm (more drift since) falls back to the inline compute"; "defer mode keeps pure-conversation sends on the quick path"; "defer mode renders a prepared warm verdict on the send path"; "warm-embedded focus reuses the verdict state (no double probe)".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-fovea", query: "warmSync warmCache deferred probe", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-lane split: eager background warm keyed by drift identity, defer-or-render on interactive sends with a TTL probe for external edits, unconditional full sync at turn end. Adapt debounce/TTL constants to your UI's latency budget. Omit the pi hook names.
