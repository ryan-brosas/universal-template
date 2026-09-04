<!-- capsule-v2 -->
# Caffeinate preferences persistence — how do user settings survive upgrades without a strict schema dropping them?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853f4bed28f7a0cca14dd1c02f54b86d6fa`; Codebase Memory `localterm`. **Question:** How do I add fields to an on-disk preferences file over time so old files migrate instead of failing validation and silently resetting to defaults?

## Version-stepped migration in front of strict zod validation
**Path/Symbol:** `packages/server/src/caffeinate-preferences-store.ts:CaffeinatePreferencesStore.load` (123–174) + `sanitizeCommands` (44–49) + `persist` (176–189).
**Signature:** `constructor(filePath: string)` (loads synchronously); setters return the effective value; file `~/.localterm/caffeinate.json`.
**Data Shape:** `{version: 4, mode, activityGate, peerKeepAwake, batteryThreshold: number|null, commands: string[]}`; defaults = automatic mode, gate on, peer on, floor 20%, no custom commands.

### Decisive source
```ts
// :137-160 — migrate ONE step at a time; each step bumps version unconditionally
if (record.version === 1) {
  if (record.activityGate === undefined) record.activityGate = true;
  record.version = 2;
}
if (record.version === 2) {
  if (record.batteryThreshold === undefined)
    record.batteryThreshold = CAFFEINATE_BATTERY_LOW_WATER_PERCENT_DEFAULT;
  record.version = 3;
}
if (record.version === 3) {
  if (record.peerKeepAwake === undefined) record.peerKeepAwake = true;
  record.version = CAFFEINATE_PREFERENCES_FILE_VERSION;
}
```

**Flow:** read → JSON.parse (warn + defaults on failure) → IF numeric version, chain v1→v2→v3→v4 filling ONLY missing fields at each step (each step advances unconditionally so intermediate field-adds are never skipped) → zod `safeParse` (fail ⇒ warn + defaults) → adopt. Persist side: mkdir -p, write `${file}.tmp`, `renameSync` over target (atomic swap). `sanitizeCommands` runs on EVERY load and set: trim → slice to 128 chars → drop empties → dedupe by lowercased form keeping the FIRST spelling (`memoBy`) → cap count at 50. Threshold setter clamps/floors into [5,50] before the equality short-circuit.
**Invariant:** without the stepped migration a v1 file would fail the CURRENT strict schema outright and fall back to defaults — losing the user's persisted mode/commands on upgrade; "field added only when missing" preserves values a user already set at that version.
**Probe:** `packages/server/tests/caffeinate-preferences-store.test.ts::"migrates v1 files by defaulting batteryThreshold to the floor default"` (:104), `"migrates v2 files by defaulting batteryThreshold to the floor default"` (:112), `"migrates v3 files by defaulting peerKeepAwake to true"` (:122), `"falls back to defaults on an invalid file"` (:87), `"trims, drops empties, and de-duplicates commands case-insensitively"` (:74); broadcast+persistence e2e `tests/caffeinate.test.ts::"broadcasts and persists the peer keep-awake toggle"` (:224 — asserts persisted `version === 4`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "CaffeinatePreferencesStore load", limit: 5 });
// → CaffeinatePreferencesStore.load @ caffeinate-preferences-store.ts:123-174 (+ AutomationStore.load/SecretStore.load twins)
```

## Verdict
Adopt the version-stepped migration pattern + first-spelling-wins normalization + tmp/rename atomicity verbatim (general-purpose persistence contract); adapt the field set/defaults/limits to host; omit the specific caffeinate semantics. Direct tests pin every migration rung and the sanitize ladder.
