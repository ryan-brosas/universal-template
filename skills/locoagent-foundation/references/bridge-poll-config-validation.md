<!-- capsule-v2 -->
# Poll-config validation — how do you make a remote timing config impossible to tight-loop?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you accept ops-tunable poll/heartbeat intervals from a feature flag while structurally forbidding configs that hammer the server or disable all liveness?

## Path/Symbol
**Path/Symbol:** `src/bridge/pollConfig.ts` — `pollIntervalConfigSchema` (:28-92), `getPollIntervalConfig` (:102-110); defaults + server-TTL constants in `src/bridge/pollConfigDefaults.ts` (:13-82: not-at-capacity 2000ms, at-capacity 600_000ms vs BRIDGE_LAST_POLL_TTL=4h, heartbeat default 0 vs 300s lease TTL, reclaim_older_than_ms 5000, keepalive 120_000).
**Signature:** `getPollIntervalConfig(): PollIntervalConfig` — GrowthBook flag `tengu_bridge_poll_interval_config`, 5-min refresh; `safeParse` failure ⇒ whole-object fallback to DEFAULT.
**Data Shape:** 8 fields incl. multisession twins; `.default()` on every optional field so old configs without new keys parse unchanged (rollout-safe).

### Decisive source
```ts
// The object-level refines require at least one at-capacity liveness
// mechanism enabled: heartbeat OR the relevant poll interval. Without this,
// the hb=0, atCapMs=0 drift config (ops disables heartbeat without
// restoring at_capacity) falls through every throttle site with no sleep —
// tight-looping /poll at HTTP-round-trip speed.
.refine(cfg =>
    cfg.non_exclusive_heartbeat_interval_ms > 0 ||
    cfg.poll_interval_ms_at_capacity > 0, {...})
// The at_capacity intervals use a 0-or-≥100 refinement: 0 means "disabled"
// (heartbeat-only mode), ≥100 is the fat-finger floor. Values 1–99 are
// rejected so unit confusion (ops thinks seconds, enters 10) doesn't poll
// every 10ms against the VerifyEnvironmentSecretAuth DB path.
```

**Flow:** schema validation IS the safety mechanism, applied at read time on every loop iteration (callers re-read per cycle so flag pushes land within one sleep). Three defense layers: (1) `.min(100)` floors restore the old `Math.max(...,100)` clamp but as Zod rejection — **one bad field rejects the WHOLE object**, no partial trust; (2) the 0-or-≥100 refinement encodes "0 = deliberately disabled" as distinct from "small number typo"; (3) cross-field refines require heartbeat OR poll liveness per loop flavor. Heartbeat named `non_exclusive_*` to distinguish from legacy either-or semantics (#22145): heartbeat now runs ALONGSIDE at-capacity polling.

**Invariant:** (1) Reject-whole-object over clamp: clamping silently trusts 7 bad-adjacent fields; rejection falls back to known-good defaults. (2) Every throttle-site combination must be provably non-zero-sleep — the refines exist precisely because two independently-valid zeros compose into a tight loop. (3) Defaults must mirror across single/multisession fields so pre-field configs preserve behavior. (4) Server-side TTLs (4h env archive, 300s lease) bound the values from above; document them in the defaults file, not just comments.

**Probe:** coverage caveat — no upstream unit tests. Deterministic pins: `grep -n "tight-looping /poll" src/bridge/pollConfig.ts` (:23-24); `grep -n "partially trusted" src/bridge/pollConfig.ts` (:12); `grep -n "work_v1.py:230" src/bridge/pollConfig.ts` (:66); graph resolves `locoagent.src.bridge.pollConfig.getPollIntervalConfig` :102-110 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "getPollIntervalConfig pollIntervalConfigSchema non_exclusive_heartbeat zeroOrAtLeast100", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt the three-layer validation grammar wholesale for any remotely-tunable timing config. Adapt field names/intervals to your TTLs; omit the multisession twins if you have one loop shape. Porting trap: copying only the min() floors and skipping the object refines reintroduces the hb=0/atCap=0 tight loop.
