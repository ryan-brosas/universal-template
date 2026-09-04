<!-- capsule-v2 -->
# Capability combustion advisory — how do you surface "captured tools match your prompt" hints at most once per source, with one-way saturation and self-calibrating confidence?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** how does a prompt-driven capability recommender avoid repeat nagging, vocabulary collision, and stale state across forks/rewinds?

## Ash (one-way burn) + warmth EWMA + smoke feedback
**Path/Symbol:** `src/core/capability-advisory.ts:CapabilityAdvisor` (:135-410), constants (:15-41), `restoreAshFromEntries` (:163-210), `evaluate` (:247-409); fingerprint index in `src/core/capability-fingerprint.ts:buildCapabilityIndex` (:54-96).
**Signature:** `evaluate(prompt: string, config: {mode; threshold; budget; maxPerSession}): CapabilityAdvisoryResult | undefined`; `observeToolUse(namespace): boolean`; `endTurn(): void`; `restoreAshFromEntries(entries, nameToNamespace)`.
**Data Shape:** per-namespace state = ash `Map<ns, {origin: "fired"|"organic", at}>`, warmth `Map<ns, number>`, plus transients `pendingFire`/`hitsThisTurn`/`smokeStreak`/`firedTotal`. Combustion constants: score quantum q=1, weak band = 1 quantum, τ=2 → warm α=0.5, smoke step θ/τ²=0.25, smoke ceiling τ²=4.

### Decisive source
```ts
// Score with 1/df term weights, NOT raw idf: idf magnitude collapses on small
// catalogs (ln(4/2) < 1), silently starving matches below threshold.
if (matchedTerms.length < 2 || score < config.threshold) continue; // ≥2 shared terms:
const strong = score >= config.threshold + WEAK_MATCH_BAND;        // lone word = collision
if (!strong) {
  const warmth = (this.#warmth.get(ns) ?? 0) + (1 - WARM_ALPHA) * score;
  this.#warmth.set(ns, warmth);
  if (warmth < ignitionPoint) continue;   // ignitionPoint = threshold*(1 + SMOKE_STEP*streak)
}
// After firing: irreversible spend — misfires are never reclaimed ("you don't
// unburn paper"); organic use burns too. Warmth is cleared on fire.
this.#burn(match.namespace, "fired", new Date().toISOString());
this.#warmth.delete(match.namespace);
this.#pendingFire.add(match.namespace);
```
```ts
// Ash derives from the TRANSCRIPT, not a side store: fired hints are custom
// messages (customType pi-fabric-capability), organic use is the persisted
// toolCall entries. Replay rebuilds ash exactly up to the current leaf, so
// forks/rewinds see period-correct ashes; replace-not-accumulate on re-replay.
```

**Flow:** tokenize prompt minus pi's `<available_skills>/<skill>` XML envelope (skill text would poison the fingerprint with its own vocabulary) → score unburned sources by Σ 1/df over shared terms → strong fires instantly, weak accumulates warmth across turns until it breaches the (smoke-raised) ignition point → render a budget-squeezed ladder of rungs (bullets+descriptions → bullets → flat refs → header+steer floor) capped at 2 sources / 3 names → mark fired, register pendingFire; `endTurn()` converts an ignored fire into smoke which raises the next ignition point and resets when a fired hint leads to real tool use.
**Invariant:** every namespace burns AT MOST ONCE per session history (`#burn` idempotent, append-only); single-term matches can never fire; ash must be reconstructible purely from transcript replay so branch navigation keeps it consistent; per-session fire cap counts evaluations that returned a result.
**Probe:** `tests/capability-advisory.test.ts:64` ("fires unambiguous matches instantly; weak-band sources need sustained exposure" — weak asymptote crosses θ=0.9 on the 4th identical prompt), `:128` ("never fires twice for the same source"), `:219` ("ignores prompt regions wrapped in pi's skill envelope"), `:271`/:308`/:322` (ash replay up to branch point, replace semantics), `:347` (organic poisoning permanent), `:381` ("raises the weak-band ignition point after an ignored fire (smoke)"), `:395` (clean combustion resets streak).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "CapabilityAdvisor evaluate ash warmth smoke ignition restoreAshFromEntries buildCapabilityIndex", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the once-per-source burn model with transcript-derived recovery, the ≥2-shared-term gate, and 1/df scoring for small catalogs; adapt τ/threshold/budget constants and rendering vocabulary to your host; omit the fovea-style presentation specifics if your UI differs.
