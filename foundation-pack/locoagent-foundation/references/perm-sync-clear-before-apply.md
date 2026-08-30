<!-- capsule-v2 -->
# Rule sync clear-before-apply — why empty groups must still produce replaceRules

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** When settings on disk change (a rule deleted), how do you make the in-memory permission context converge instead of silently keeping stale rules?

## Path/Symbol
**Path/Symbol:** `src/utils/permissions/permissions.ts` — `syncPermissionRulesFromDisk` (:1419-1471), `convertRulesToUpdates` grouping (:1375-1403), `applyPermissionRulesToPermissionContext` additive variant (:1408-1414); `src/utils/permissions/permissionsLoader.ts` — `loadAllPermissionRulesFromDisk` managed-only gate (:120-133).
**Signature:** `syncPermissionRulesFromDisk(context: ToolPermissionContext, rules: PermissionRule[]): ToolPermissionContext`.
**Data Shape:** Updates are grouped per `source:behavior`; `replaceRules` swaps the whole array for one destination; `addRules` appends.

### Decisive source
```ts
// Clear all disk-based source:behavior combos before applying new rules.
// Without this, removing a rule from settings (e.g. deleting a deny entry)
// would leave the old rule in the context because convertRulesToUpdates
// only generates replaceRules for source:behavior pairs that have rules —
// an empty group produces no update, so stale rules persist.
const diskSources: PermissionUpdateDestination[] = [
  'userSettings', 'projectSettings', 'localSettings',
]
for (const diskSource of diskSources) {
  for (const behavior of ['allow', 'deny', 'ask'] as PermissionBehavior[]) {
    context = applyPermissionUpdate(context, {
      type: 'replaceRules', rules: [], behavior, destination: diskSource,
    })
  }
}
```

**Flow:** managed-only mode (`allowManagedPermissionRulesOnly` in policySettings) → wipe ALL non-policy sources first (:1426-1446) → unconditionally clear every disk-based source×behavior combo → apply the freshly loaded rules as grouped `replaceRules`. The ADDITIVE twin (`applyPermissionRulesToPermissionContext`) is used once at startup; the REPLACING twin is used on settings changes.

**Invariant:** (1) Grouping-only sync can never delete a rule — absence of updates is not a deletion protocol; clearing empty combos first is what makes removal propagate. (2) In-memory sources (`session`, `cliArg`) survive a disk re-sync EXCEPT under managed-only mode, which wipes them too (enterprise policy outruns session grants). (3) Startup uses add; runtime uses replace — mixing them up makes hot-reload accumulate duplicates.

**Probe:** coverage caveat — no upstream unit tests reachable. Deterministic pins from repo root: `grep -nF 'an empty group produces no update, so stale rules persist' src/utils/permissions/permissions.ts` → :1452; `grep -nF 'shouldAllowManagedPermissionRulesOnly()) {' src/utils/permissions/permissions.ts | head -1` → :1426; graph search `syncPermissionRulesFromDisk` → :1419-1471 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "convertRulesToUpdates applyPermissionUpdates replaceRules stale", limit: 5 });
```

## Verdict
Adopt clear-before-apply over diffing for settings hot-reload, and the managed-only total wipe. Adapt destination names to your storage layers. Omit nothing else.
