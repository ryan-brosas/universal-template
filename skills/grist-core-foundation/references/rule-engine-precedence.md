<!-- capsule-v2 -->
# Granular access rule engine — how does Grist evaluate ACL rule sets into a permission for a column, table, or whole doc, and how does it merge the four-state permission algebra?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** Given a user (and optionally a record), how does Grist turn the `_grist_ACLRules` rule sets into a single `PermissionSet` per column/table/doc, and what merge algebra decides `allow`/`deny`/`mixed`/`mixedColumns`?

## Precedence ladder + four-state merge algebra + pessimistic error handling
**Path/Symbol:** `app/server/lib/PermissionInfo.ts` — `RuleInfo` abstract base (:70-122), `PermissionInfo` (:166-236), `evaluateRule` (:248-305), `MemoInfo` (:128-153), `isCertainPermission` (:239-241); `app/common/GranularAccessClause.ts` — `RuleSet`/`RulePart` types (:6-25).
**Signature:** `PermissionInfo extends RuleInfo<MixedPermissionSet, TablePermissionSet>`; `getColumnAccess(tableId, colId): MixedPermissionSetWithContext` (:174-180), `getTableAccess(tableId): TablePermissionSetWithContext` (:186-192), `getFullAccess(): MixedPermissionSetWithContext` (:197-203); `evaluateRule(ruleSet, input): PartialPermissionSet` (:248-305).
**Data Shape:** `RuleSet = { tableId, colIds: "*"|string[], body: RulePart[] }` where the default rule is a `RulePart` with `aclFormula: ""` that MUST be the last element of `body`; `RulePart = { aclFormula, permissions: PartialPermissionSet, permissionsText, matchFunc?, memo? }`. Permission values are the four-state algebra `allow`/`deny`/`mixed`/`mixedColumns` (plus partial `allowSome`/`denySome`/`""` during evaluation).

### Decisive source
```ts
// RuleInfo — the precedence ladder: column rules first, then table default, then doc default.
public getColumnAspect(tableId, colId) {
  const ruleSet = this._acls.getColumnRuleSet(tableId, colId);
  return ruleSet ? this._processColumnRule(ruleSet) : this._getTableDefaultAspect(tableId);
}
private _getTableDefaultAspect(tableId) {
  const ruleSet = this._acls.getTableDefaultRuleSet(tableId);
  return ruleSet ? this._processRule(ruleSet, () => this._getDocDefaultAspect()) : this._getDocDefaultAspect();
}
private _getDocDefaultAspect() { return this._processRule(this._acls.getDocDefaultRuleSet()); }
```
```ts
// PermissionInfo._processRule — memoized per RuleSet; mask applies allow/deny override; toMixed at the end.
protected _processRule(ruleSet, defaultAccess?) {
  return getSetMapValue(this._ruleResults, ruleSet, () => {
    let pset = evaluateRule(ruleSet, this._input);
    pset = defaultAccess ? mergePartialPermissions(pset, defaultAccess()) : pset;
    if (this._input.mask) {
      pset = mergePermissions([pset, this._input.mask], ([val, mask]) => mask === "allow" ? val : "deny");
    }
    return toMixed(pset);
  });
}
```
```ts
// _mergeTableAccess — per-column merge produces the four-state algebra.
return mergePermissions(access, bits => (
  bits.every(b => b === "allow") ? "allow" :
  bits.every(b => b === "deny") ? "deny" :
  bits.every(b => b === "allow" || b === "deny") ? "mixedColumns" :
  "mixed"
));
```

**Flow:** `evaluateRule` walks `ruleSet.body` in order, merging each passing rule's `permissions` via `mergePartialPermissions`; a `NEED_ROW_DATA` throw (rule needs `rec` but none supplied) merges the rule as `allowSome`/`denySome` partials — and, when the rule carries a memo, converts `denySome` on the data-change bits (`create`/`update`/`delete`) to `mixed` so the optimizer is forced to scan rows and can later attribute the denial to a specific rule. Any OTHER exception is interpreted pessimistically: `allow` → `""` (drop the allowance), `deny` stays, with a `log.warn` naming the doc/table/formula. `PermissionInfo._processRule` memoizes per `RuleSet` in `_ruleResults`, merges the lower-precedence default, applies an optional `mask` (allow overrides, deny forces), and finalizes to `toMixed`. The four-state merge: all-allow→`allow`, all-deny→`deny`, mix-of-only-allow/deny→`mixedColumns` (columns differ but no row dependence), anything else→`mixed` (row-dependent). `getTableAccess` sets `ruleType` to `"row"` when `_input.rec` is present else `"table"`; `getColumnAccess`/`getFullAccess` always report `"column"`/`"full"`.
**Invariant:** the default rule is the LAST element of `body` and is merged as the lowest-precedence fallback — a porter must not reorder it. `mixed` is a FINAL state that disables optimizations (forces row checks) and can't be combined further; `allowSome`/`denySome` are transient and always resolve to `allow`/`deny`/`mixed`. The `NEED_ROW_DATA`→`denySome`→`mixed` conversion is the deliberate mechanism that makes memo attribution possible without pre-scanning rows — it trades a table/column-level denial for a forced row scan.
**Probe:** `test/server/lib/GranularAccess.ts` — "forces a row check for rules with memo and rec" (:239-460) pins the denySome→mixed conversion and memo attribution across -U/-C/-D; "reports memos sensibly" (:906+) pins reason/remedy memo semantics.
**Coverage caveat:** the `RuleSet`/`RulePart` shapes in `GranularAccessClause.ts` are data contracts (no direct unit test); the mask path (`_input.mask`) has no dedicated test.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "PermissionInfo getColumnAccess getTableAccess getFullAccess evaluateRule extractMemos", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the column→table→doc precedence ladder, the four-state merge algebra with `mixedColumns` distinguishing column-only from row-dependent variance, the memoized per-rule-set evaluation, the `NEED_ROW_DATA`→`denySome`→`mixed` memo-forcing conversion, and the pessimistic unexpected-error handling; adapt the rule source (any `{tableId, colIds, body}` collection) and the predicate language; omit the Grist-specific memo wording if your engine doesn't surface denial explanations.
