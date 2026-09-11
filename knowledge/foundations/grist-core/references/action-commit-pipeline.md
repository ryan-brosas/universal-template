<!-- capsule-v2 -->
# OT Action Commit Pipeline — how does a user action travel from API call to durable storage, broadcast, and (on rejection) a consistent revert?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** What is the serialization and failure-recovery structure for applying collaborative document actions when the compute engine is a separate process?

## Two-mutex pipeline: engine-first, then one SQLite txn, then broadcast — with nondeterministic-formula salvage
**Path/Symbol:** `app/server/lib/Sharing.ts` (whole file, 370L) — public gate `addUserAction` (62–71) under `_userActionLock`; core `_doApplyUserActions` (73–230); engine step + revert ladder `_applyActionsToDataEngine` (242–302); salvage math `_createExtraBundle` (329–356); envelope helper `findOrAddAllEnvelope` (365–370). Upstream callers: `ActiveDoc._applyUserActions` (`app/server/lib/ActiveDoc.ts:2545–2588`, clears `_fetchCache` + audit-log on `isModification`) behind `_applyUserActionsWithExtendedOptions` (2697–2717, delete-only-mode guard).
**Signature:** `addUserAction(docSession, action: UserActionBundle): Promise<ApplyUAResult>`; internal `ApplyResult { failure?: Error, result?: { accessControl, bundle: SandboxActionBundle } }`.
**Data Shape:** `UserActionBundle {info, options, userActions}` in; `SandboxActionBundle {envelopes, stored[], calc[], direct[], undo[], retValues, rowCount}` back from the engine; `LocalActionBundle` adds `actionNum`, `actionHash`, and the all-recipients envelope index.

### Decisive source
```ts
const { result, failure } =
  await this._modificationLock.runExclusive(() => this._applyActionsToDataEngine(docSession, userActions, options));
if (failure && !result) { throw failure; }        // clean ACL rejection
...
if (!trivial) {
  await this._activeDoc.docStorage.execTransaction(async () => {
    await this._activeDoc.applyStoredActionsToDocStorage(getEnvContent(localActionBundle.stored));
    await this._actionHistory.recordNextShared(localActionBundle);   // data + history commit together
    if (client?.clientId && !internal) { this._actionHistory.setActionUndoInfo(...); }
  });
}
await this._activeDoc.processActionBundle(localActionBundle);      // in-memory mirror + index upkeep
// Rejected actions with side effects (NOW()/UUID() formulas):
const extraBundle = this._createExtraBundle(undoResult, getEnvContent(applyResult.undo));
return { result: { bundle: extraBundle, accessControl }, failure: applyExc };  // persist extras + report failure
```
Salvage invariant inside `_createExtraBundle`: reversed undo actions must EXACTLY prefix-match what the engine stored (`storedHead.every(isEqual)`), else hard-fail; only the suffix beyond the sent actions becomes the fake bundle.

**Flow:** `_userActionLock` serializes whole pipelines → `_modificationLock` guards just the engine round-trip → on ACL rejection the engine is told to `ApplyUndoActions`; if the undo produced EXTRA stored actions (nondeterministic formulas), those extras are re-checked against access rules and persisted so engine and DB stay byte-identical while the caller still receives the failure → otherwise data+history land in ONE SQLite transaction → webhooks/triggers fire (single `Calculate` suppressed to avoid a doc-load deadlock), row counts sync, action broadcasts to clients, `finishedBundle()` runs in `finally` even on misc errors. Trivial bundles (system/internal actions storing nothing) skip actionNum allocation entirely. Shutdown race handled: a system action arriving during shutdown returns a trivial success.
**Invariant:** the data engine is ALWAYS mutated first and reverted there — SQLite only ever sees post-validation state, so DB transactions never need compensating actions. Every accepted bundle commits stored-data and action-history atomically; undo info is registered per-client INSIDE that same transaction. A rejected action may still durably persist its formula side effects, but ONLY after exact-prefix verification proves which effects were real. If the revert itself throws, the doc is shut down hard (unrecoverable divergence). Two different mutexes are deliberate: queueing fairness for user calls vs strict engine serialization.
**Probe:** direct tests: `test/server/lib/ActiveDocShutdown.ts:183` "should close ActiveDoc in infinite loop after timeout" pins the Calculate/shutdown interplay, :60/:72/:112/:144 pin client/import/load hold-open behavior around the pipeline; BundleActions.ts (:1–120) pins linkId chaining semantics set at :217 of Sharing.ts. No dedicated Sharing unit file exists (coverage caveat) — behavior is pinned through ActiveDoc-level suites.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "Sharing addUserAction _createExtraBundle processActionBundle", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt this shape for any "external compute engine + durable store" collaboration server: engine-first validation, single-txn persistence of data+history, and the side-effect-salvage contract transfer directly. Adapt envelope/recipient machinery to your broadcast model and the trivial-bundle predicate to your action vocabulary. Omit the extra-bundle salvage only if your formulas are deterministic by construction — but then enforce that with tests, because the salvage path exists precisely because grist's weren't.
