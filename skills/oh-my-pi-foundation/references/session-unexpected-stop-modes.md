<!-- capsule-v2 -->
# Unexpected-stop detection modes — how do you migrate a boolean feature flag to a tri-state enum without silently re-enabling it for users who explicitly turned it off?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@4854db85`; Codebase Memory `oh-my-pi`. **Question:** What is the settings-migration contract for `features.unexpectedStopDetection` boolean→enum, and how do the mechanical/smart modes differ in TurnRecovery?

## Boolean→enum migration with off-preserving semantics
**Path/Symbol:** `packages/coding-agent/src/config/settings.ts:` migration block (:1608–1631); schema `src/config/settings-schema.ts` (enum `none|mechanical|smart`, default `mechanical`); consumer `src/session/turn-recovery.ts` (classification only in smart mode).
**Signature:** Settings migration over raw config: reads BOTH `features.unexpectedStopDetection` object key AND flat `features.unexpectedStopDetection` dotted key.
**Data Shape:** Legacy `true` → `"smart"`; legacy `false` → `"none"`; absent → new default (`mechanical`). Enum validated by membership list `["none","mechanical","smart"]`.

### Decisive source
```ts
// features.unexpectedStopDetection (boolean) -> enum none|mechanical|smart.
// ... now "smart"; `false` maps to "none" so explicitly disabled configs remain
// off rather than inheriting the new "mechanical" default.
const currentIsMode = typeof current === "string" && ["none", "mechanical", "smart"].includes(current);
if (!currentIsMode) {
	target.unexpectedStopDetection = legacyUnexpectedStop ? "smart" : "none";
}
delete raw["features.unexpectedStopDetection"];
```

**Flow:** settings load → migration detects legacy boolean at either the nested or flat dotted key → converts per the mapping → DELETES the legacy key from raw so later passes never see stale shapes → TurnRecovery branches on mode: `smart` performs LLM classification of why a turn stopped unexpectedly; `mechanical` applies deterministic heuristics only and SKIPS classifier calls; `none` disables both. The classifier module itself changed by exactly ONE line across this drift (signature/type accommodation) — the behavioral surface is the settings gate + recovery branching.
**Invariant:** Explicitly-disabled must stay disabled: `false→"none"` even though the new default is `"mechanical"` — inheriting a default would flip opt-out users into the feature. The migration must consume BOTH spellings of the key (nested object + dotted flat form) because settings files persist both shapes, and must delete the legacy key after converting.
**Probe:** Settings behavior verified byte-exact at pin: `sed -n '1626,1630p' src/config/settings.ts` shows the conversion verbatim; `grep -c legacyUnexpectedStop src/config/settings.ts` → 3 (executed green). Adjacent empty-stop retry behavior pinned by `test/agent-session-empty-stop-guard.test.ts` (`"caps empty stop retries at three attempts and discards the final empty turn"` :378).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "unexpectedStopDetection enum mechanical smart migration settings", limit: 10, fields: ["signature", "name", "file"] });
```
BM25 caveat: the migration lives inside a large function body; if graph search misses, resolve via `search_code --pattern unexpectedStopDetection --file-pattern settings.ts` (line-exact Module resolution is the working primitive on settings files).

## Verdict
Adopt the three-way migration mapping (true→new-feature-mode, false→hard-off, absent→default) and dual-key consumption for ANY boolean→enum flag migration. Adapt mode names/classifier wiring to your host. Omit the upstream CHANGELOG churn.
