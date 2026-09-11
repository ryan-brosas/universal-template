<!-- capsule-v2 -->
# Turn-sync surprise gate — how do you wake the model for real drift but never twice for the same edit?

**Source:** pi-fovea MIT `DETACHED@217a103`; Codebase Memory `pi-fovea`. **Question:** Continuous post-turn repo sync must steer (inject context + continue an idle agent) on meaningful changes, stay silent on comment/formatting churn and re-disclosures, and never fire a false red on extraction gaps — what is the verdict algebra?

## Per-node charged heat memory + channel priors + evidence-gated anchors
**Path/Symbol:** `src/core/sync.ts:sync/warmSync/semanticFacts/decayedMass/gitDriftSince` (:92-591); constants `CHANNEL_WEIGHT` (:127-138), `MEMORY_HALF_LIFE_HOURS` (:144), `MEMORY_MAX_NODES=4096`, `REARM_FRACTION=0.5`; baseline store on global slot (:54-86).
**Signature:** `sync(root, params: SyncParams, now?: RepoState, opts?: { probe: "cheap"|"full"|"defer" }): Promise<SyncOutcome>`; `decayedMass(entry {m,t}, nowMs) = m · 0.5^(Δt/halfLifeMs)`.
**Data Shape:** `SyncBaseline = { version, anchors: Map<id,carrierFile>, shas, semantics, heat?: Map<"kind|name@file", {m,t}>, warmthArmed?, pushed? }`. Semantic fingerprint per file = JSON of sorted [name,kind,compactSig,lang] / import specs / callees / literal texts / anchor tuples — whitespace-insensitive, WeakMap-cached.

### Decisive source
```ts
// Surprise is measured PER GRAPH NODE against a wall-clock-decayed ledger:
const nodeMass = (hit) => hit.m * Math.max(...hit.r.map(r => CHANNEL_WEIGHT[r] ?? 0.5));
for (const [key, hit] of Object.entries(warmNodes)) {
  if (disclosedFiles.has(hit.file) || files.includes(hit.file)) continue;
  const delta = nodeMass(hit) - (memory.get(key)?.m ?? 0);
  if (delta > 1e-9) { surprise.set(hit.file, ...); surpriseTotal += delta; }
}
// Hysteresis latch: any red sync disarms warmth until total surprise drops
// back into the re-arm fraction of the threshold.
const warmthFire = prevArmed && surpriseTotal >= params.steerThreshold;
const red = structuralRed || warmthFire;
const warmthArmed = red ? false : prevArmed || surpriseTotal <= params.steerThreshold * REARM_FRACTION;
if (red) // absorb-on-disclosure: charge every warmed cascade node at adjusted mass

// Anchor deltas need carrier evidence — extraction gaps look like removals:
const degraded = state.extraction.failed.length > 0;
const evidence = new Set([...changed, ...semanticChanged, ...deleted]);
const suspectRemoved = removed.filter((id) => !evidence.has(prev.anchors.get(id) ?? ""));
const structuralRed = (evidentialAdded.length - newlyImplicit.length) > 0 ||
  (evidentialRemoved.length > 0 && !degraded) ||
  deleted.some((file) => !isTestScope(file));
```

**Flow:** fast paths first — resident version == baseline → silent no-op; no baseline or a checkout generation (`gitReflogAction().startsWith("checkout:")`) → snapshot silently ("first contact is never red"; branch diffs are not authored drift); send path (`probe:"defer"`) never rebuilds — TTL-bounded porcelain probe (`PROBE_TTL_MS=1200`) defers hintless drift to turn_end's full sync, but renders an already-prepared warm verdict. Real drift: semantic fingerprint diff (comment-only edits change sha but not semantics → green), impact cascade over changed files → channel-adjusted per-node mass minus decayed ledger → threshold verdict → push (embed top target's focus once per baseline chain) or pull ("Next: fovea_focus …") → deliver as steer with `triggerTurn`.
**Invariant:** The ping-pong constructor dies BY CONSTRUCT: re-editing the same spot re-seeds identical node keys whose ledger was charged at disclosure, so every later flip's surprise is rounding noise (< 0.005 vs 0.05 threshold) — suppression is by charged KEY, never by file or blanket, so a novel hunk in a known file still fires. Absent-from-facts + still-on-disk is a coverage gap, NOT a deletion (existsSync check kills the phantom-deletion loop). Implicit/discovered anchors report but NEVER escalate alone.
**Probe:** `tests/sync.test.ts` — "charged node memory kills the ping-pong by construct, on every flip" (5 poles all silent); "gates on surprise mass, not warmed-file count" (threshold 8 stays quiet at ≈0.077 mass); "re-baselines quietly on a branch switch"; "never reports an on-disk file as deleted"; "warm path equals the inline compute on the same drift"; "defer mode never rebuilds… leaves it to the backstop".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-fovea", query: "surprise steerThreshold warmthArmed baseline", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the whole verdict algebra: semantic fingerprints over content hashes, per-node charged ledger with wall-clock half-life (48h default), channel priors (call/import/test/inheritance/route=1, co-change/graph-path=0.5, shared-literal=0.35), hysteresis disarm/re-arm, carrier-evidence gating for anchor deltas, defer-on-send-path + turn_end backstop. Adapt priors/thresholds to your graph's edge semantics. Omit the pi-specific hook wiring (`deliverAs:"steer"`).
