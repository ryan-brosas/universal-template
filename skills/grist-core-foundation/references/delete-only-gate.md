<!-- capsule-v2 -->
# Delete-Only Mode Gate — how do you freeze a document to deletions-only at the action-application boundary?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** When a document exceeds its plan limits, what single choke point turns off all non-destructive user actions, and which action kinds are still allowed through?

## Allowlist gate at the extended-options entry point
**Path/Symbol:** `app/server/lib/ActiveDoc.ts` — `_applyUserActionsWithExtendedOptions` (:2696–2717), specifically the `dataLimitInfo.status === "deleteOnly"` guard (:2705–2713); status source `dataLimitInfo` getter (:570–576) → `getDataLimitInfo` from `app/common/Limits.ts`.
**Signature:** `_applyUserActionsWithExtendedOptions(docSession, actions: UserAction[], options?): Promise<ApplyUAResult>`.
**Data Shape:** guard inspects `this.dataLimitInfo.status`; if `"deleteOnly"`, every action's `action[0]` kind must be in the allowlist else `throw new Error("Document is in delete-only mode")`.

### Decisive source
```ts
if (
  this.dataLimitInfo.status === "deleteOnly" &&
  !actions.every(action => [
    "RemoveTable", "RemoveColumn", "RemoveRecord", "BulkRemoveRecord",
    "RemoveViewSection", "RemoveView", "ApplyUndoActions", "RespondToRequests",
  ].includes(action[0] as string))
) {
  throw new Error("Document is in delete-only mode");
}
```
Placed at the TOP of `_applyUserActionsWithExtendedOptions`, i.e. BEFORE `_applyUserActions` → before granular-access checks and before `Sharing.addUserAction`. Note the two public entry points that route here: `applyUserActions` (sanitizes options then calls this) and `applyWebhookActions` (waives the schema-edit check for `_grist_Triggers` only, :1641–1648) — both funnel through this same gate.

**Flow:** status is derived from usage vs. plan features + grace period (`getDataLimitInfo`) → every user-action application checks the allowlist → a single disallowed kind rejects the whole batch (no partial application) → allowed kinds (pure deletions + undo + request responses) proceed to granular access and the OT pipeline.
**Invariant:** (1) The gate is ALLOWLIST, not denylist: adding a new mutating action kind silently stays blocked until explicitly added — a safe default for a freeze. (2) It is enforced at the shared extended-options funnel so no public entry path can bypass it. (3) `ApplyUndoActions` is permitted, meaning undo of earlier destructive changes still works in delete-only mode. (4) It fires before access-control checks, so it is a hard product-level freeze independent of who the caller is.
**Probe:** no direct unit test asserts the delete-only string (grep over `test/` for `delete-only mode` returns none) — coverage caveat: behavior is exercised indirectly through plan/limit suites and the `dataLimitInfo` status tests; the allowlist membership is verified by source inspection only.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "deleteOnly _applyUserActionsWithExtendedOptions dataLimitInfo", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the pattern: a single allowlist gate at the write funnel, derived from a plan/usage status, that rejects whole batches on the first disallowed kind and lets undo/request-responses through. Adapt the exact action vocabulary to your host. Omit Grist's specific action names unless you share its schema. Caveat: no direct test pins the allowlist — verify membership by reading the source before porting.
