<!-- capsule-v2 -->
# Granular access bundle lifecycle — how does a user-action edit travel through the ACL engine's five phases, and where do the two mutexes sit?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** What is the exact call ordering that keeps access control, the OT commit pipeline, and per-client broadcast consistent for one edit?

## Bundle state machine + two-mutex pipeline
**Path/Symbol:** `app/server/lib/GranularAccess.ts` — `getGranularAccessForBundle` (:321-335), `checkUserActions` (:929-952), `canApplyBundle` (:596-677), `appliedBundle` (:702-720), `finishedBundle` (:727-737), `_hasExceptionalFullAccess` (:1235-1237); the engine round-trip + revert ladder live in `app/server/lib/Sharing.ts` (`_applyActionsToDataEngine` :242-302) under `_modificationLock`, whole pipeline under `_userActionLock` (see action-commit-pipeline.md).
**Signature:** `getGranularAccessForBundle(docSession, docActions, undo, userActions, isDirect, options): void` — throws if a bundle is already in progress; `canApplyBundle(): Promise<void>`; `appliedBundle(): Promise<void>`; `finishedBundle(): Promise<void>`.
**Data Shape:** `_activeBundle = { docSession, docActions, undo, userActions, isDirect, applied:false, hasDeliberateRuleChange, hasAnyRuleChange, maybeHasShareChanges, options }`. `isDirect[i]` marks whether docAction[i] was a direct user action (vs a formula/Calculate side effect) — only direct ones get re-checked.

### Decisive source
```ts
// Sharing._doApplyUserActions — the two-mutex ordering
const { result, failure } =
  await this._modificationLock.runExclusive(() => this._applyActionsToDataEngine(docSession, userActions, options));
if (failure && !result) { throw failure; }          // clean ACL rejection, nothing persisted
// ... engine produced a SandboxActionBundle; access control is started BEFORE persisting:
let accessControl = this._startGranularAccessForBundle(docSession, applyResult, userActions, options);
// canApplyBundle() is called before the SQLite txn; if it throws the sandbox changes are reverted.
// appliedBundle() after the txn; finishedBundle() in a finally even on misc errors.
```

**Flow:** `_userActionLock` serializes whole pipelines → `_modificationLock` guards only the engine round-trip → `getGranularAccessForBundle` snapshots the bundle (throws if one is already live — bundles never nest) → `checkUserActions` does the coarse pre-engine checks → the engine compiles UserActions→DocActions → `canApplyBundle` runs the definitive per-action checks (throws ⇒ sandbox revert, nothing persisted) → data+history commit in ONE SQLite txn → `appliedBundle` (post-apply, pre-broadcast: caches permission state for outgoing filtering) → broadcast → `finishedBundle` (rebuilds rules if the bundle changed ACL tables, clears `_steps`/`_metaSteps`/`_prevUserAttributesMap`/`_activeBundle`).
**Invariant:** the phases are strictly ordered and the ACTIVE bundle is the single source of truth for the whole pipeline — a porter who re-checks access after commit, or who lets two bundles overlap, breaks the revert-on-deny guarantee and the per-client broadcast filtering. `canApplyBundle` also enforces two hard gates: only owners may deliberately modify access rules (`hasDeliberateRuleChange && !userIsOwner` → ACL_DENY), and non-owners/editors cannot edit at all (`!canEdit(getNominalAccess)` → ACL_DENY). `_hasExceptionalFullAccess` (docSession.mode `system`|`nascent`) short-circuits every check — system sessions always pass.
**Probe:** `test/server/lib/GranularAccess.ts` — "rejects writes from prefork-as-owner sessions before touching the engine" (:198) pins the `checkUserActions` early guard; "persist data when action is rejected" (:632/:663/:699/:728) pins the canApplyBundle-throws ⇒ revert contract; "respects owner-only structure" (:1206) pins the owner-gate.
**Coverage caveat:** the exact phase-ordering is exercised end-to-end by the test suite's `applyUserActions` helper, not by a dedicated unit test; the revert-on-deny and broadcast-filter behaviors are pinned indirectly via the suites above.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "GranularAccess canApplyBundle appliedBundle finishedBundle getGranularAccessForBundle", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the five-phase bundle lifecycle and the two-mutex (pipeline + engine) ordering verbatim for any collaborative doc store that must revert-on-deny and filter broadcasts per client; adapt the rule source (here `_grist_ACLRules`/`_grist_ACLResources`); omit the `isDirect` formula-side-effect tracking if your engine has no background recalculation.
