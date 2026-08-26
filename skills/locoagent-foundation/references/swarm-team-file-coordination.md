<!-- capsule-v2 -->
# Team file as coordination DB — how do cross-process teammates share identity, panes, and permission modes through one JSON file?

**Source:** locoagent (Claude Code CLI fork, MIT), rev `c01bb3f`; Codebase Memory `locoagent`. **Question:** what does the team config file own, which name sanitization invariants does it depend on, and when must multi-member updates be atomic?

## TeamFile schema + sanitizeName + setMultipleMemberModes
**Path/Symbol:** `src/utils/swarm/teamHelpers.ts:TeamFile` (:64-90), `sanitizeName` (:100-102), `sanitizeAgentName` (:108-110), `getTeamDir` (:115-117), `setMultipleMemberModes` (:415-445), `setMemberActive` (:454-485).
**Signature:** `sanitizeName(name): name.replace(/[^a-zA-Z0-9]/g,'-').toLowerCase()`; `sanitizeAgentName(name): name.replace(/@/g,'-')`.
**Data Shape:** members carry agentId, name, tmuxPaneId, backendType, isActive, mode, subscriptions, worktreePath; plus hiddenPaneIds and teamAllowedPaths.

### Decisive source
```ts
export function sanitizeAgentName(name: string): string {
  return name.replace(/@/g, '-')
}
```
(setMultipleMemberModes docstring: "Sets multiple team members' permission modes in a single atomic operation. Avoids race conditions when updating multiple teammates at once." — one read-map-write cycle for N updates.)

**Flow:** every mutation follows read-modify-WHOLE-file-write (`readTeamFile` → transform immutably → `writeTeamFile`); no-op writes skipped by change detection (`if (member.mode === mode) return true`; `anyChanged` flag); sync variants exist ONLY for React render paths with explicit `// sync IO: called from sync context` comments; pane-based removal keys on tmuxPaneId while in-process removal uses removeMemberByAgentId because ALL in-process teammates share one leader pane.
**Invariant:** `@` is RESERVED as the agentId separator — sanitize it out of names or `agentName@teamName` parsing becomes ambiguous; directory names derive from the sanitized team name everywhere (getTeamDir/getTasksDir/permissionSync dirs all call sanitizeName); single-field setters may read-modify-write per call but bulk updates MUST be single-cycle.
**Probe:** coverage caveat (no direct tests). Deterministic probes: `grep -n "replace(/@/g" src/utils/swarm/teamHelpers.ts` (:109); `grep -n 'Avoids race conditions' src/utils/swarm/teamHelpers.ts` (:411).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "TeamFile sanitizeName sanitizeAgentName setMemberMode setMultipleMemberModes", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt a single JSON coordination file with strict identifier sanitization at every path-derivation boundary and atomic multi-field writes; adapt schema fields; omit worktreePath handling if you don't isolate teammates in git worktrees.
