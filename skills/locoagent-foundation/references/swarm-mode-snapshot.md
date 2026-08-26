<!-- capsule-v2 -->
# Swarm mode snapshot — how do you stop runtime config edits from flipping teammate execution mid-session?

**Source:** locoagent (Claude Code CLI fork, MIT), rev `c01bb3f`; Codebase Memory `locoagent`. **Question:** where must teammateMode ('auto'|'tmux'|'in-process') be captured so that a mid-session settings change cannot change how already-planned teammates run?

## capture-once snapshot with a UI escape hatch
**Path/Symbol:** `src/utils/swarm/backends/teammateModeSnapshot.ts:captureTeammateModeSnapshot` (:56-69), `getTeammateModeFromSnapshot` (:75-87), `setCliTeammateModeOverride` (:25-27), `clearCliTeammateModeOverride` (:43-49).
**Signature:** `captureTeammateModeSnapshot(): void`; `getTeammateModeFromSnapshot(): TeammateMode`; `clearCliTeammateModeOverride(newMode: TeammateMode): void`.
**Data Shape:** module-level `initialTeammateMode: TeammateMode | null` plus `cliTeammateModeOverride: TeammateMode | null`. Capture precedence: CLI override > `config.teammateMode ?? 'auto'`.

### Decisive source
```ts
export function clearCliTeammateModeOverride(newMode: TeammateMode): void {
  cliTeammateModeOverride = null
  initialTeammateMode = newMode
  logForDebugging(
    `[TeammateModeSnapshot] CLI override cleared, new mode: ${newMode}`,
  )
}
```
```ts
if (initialTeammateMode === null) {
  // This indicates an initialization bug - capture should happen in setup()
  logError(new Error('getTeammateModeFromSnapshot called before capture - this indicates an initialization bug'))
  captureTeammateModeSnapshot()
}
return initialTeammateMode ?? 'auto'
```

**Flow:** CLI parse sets override BEFORE capture → `captureTeammateModeSnapshot()` runs early in main.tsx after args parse → all later readers call `getTeammateModeFromSnapshot()` which NEVER re-reads config → the Settings UI cannot write globalConfig directly for this key; it MUST route through `clearCliTeammateModeOverride(newMode)` which clears the stale CLI value and updates the snapshot in one step (passing newMode as a parameter avoids read/write race).
**Invariant:** session-stable mode: runtime config changes don't affect current-session teammate mode (mirrors hooksConfigSnapshot pattern); the null-read path logs an initialization-bug error then self-heals with fallback 'auto' instead of crashing.
**Probe:** coverage caveat (no direct tests). Deterministic probe: `grep -n 'initialization bug' src/utils/swarm/backends/teammateModeSnapshot.ts` hits :79-81; consumer wiring `grep -rn 'captureTeammateModeSnapshot\|setCliTeammateModeOverride' src/main.tsx src/components/Settings/Config.tsx`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "captureTeammateModeSnapshot getTeammateModeFromSnapshot clearCliTeammateModeOverride", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt capture-once startup snapshots for any mode that decides process topology, with an explicit clear-and-set function as the ONLY sanctioned runtime mutation path; adapt the config key name; omit the ant-internal telemetry around it.
