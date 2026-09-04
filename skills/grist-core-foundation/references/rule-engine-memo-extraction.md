<!-- capsule-v2 -->
# Granular access memo extraction — how does Grist decide which denial "reason"/"remedy" memos to surface, and why a shadowed remedy is dropped while a co-equal reason is kept?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** When access is denied, which ACL memos does Grist show the user, and how does `MemoInfo` avoid showing a misleading remedy when a higher-precedence rule already settles the outcome?

## reason vs remedy + shadowed-remedy drop + NEED_ROW_DATA memo forcing
**Path/Symbol:** `app/server/lib/PermissionInfo.ts` — `MemoInfo` (:128-153), `extractMemos` (:313-346), `mergeMemoSets` (:32-49), `emptyMemoSet` (:51-59), `isCertainPermission` (:239-241); `RuleInfo.getColumnAspect`/`getTableAspect`/`getFullAspect` (:76-94).
**Signature:** `MemoInfo extends RuleInfo<MemoSet, MemoSet>`; `_processRule(ruleSet, defaultAccess?): MemoSet` (:129-144); `extractMemos(ruleSet, input): MemoSet` (:313-346); `mergeMemoSets(psets: MemoSet[]): MemoSet` (:32-49).
**Data Shape:** `MemoSet = PermissionSet<Memo[]>` (memos keyed by `read`/`create`/`update`/`delete`/`schemaEdit`); `Memo = { kind: "reason"|"remedy", text: string }`. Dedup key is `` `${memo.kind} ${memo.text}` ``.

### Decisive source
```ts
// MemoInfo._processRule — drop lower-precedence remedies once this rule set certainly settles a bit.
const perms = evaluateRule(ruleSet, this._input);
const defaultMemos = defaultAccess();
const relevantDefaults = emptyMemoSet();
for (const prop of ALL_PERMISSION_PROPS) {
  relevantDefaults[prop] = isCertainPermission(perms[prop]) ?
    defaultMemos[prop].filter(memo => memo.kind === "reason") :
    defaultMemos[prop];
}
return mergeMemoSets([pset, relevantDefaults]);
```
```ts
// extractMemos — a passing deny is a "reason"; a failing allow is a "remedy".
if (rule.memo) {
  if (passing && p === "deny") {
    pset[prop].push({ kind: "reason", text: rule.memo });
  } else if (!passing && p === "allow" && !isCertainPermission(acc[prop])) {
    pset[prop].push({ kind: "remedy", text: rule.memo });
  }
}
if (passing) { acc[prop] = combinePartialPermission(acc[prop], p); }
```

**Flow:** `extractMemos` walks the rule body accumulating a running resolved permission `acc` per bit. A memo on a rule that PASSES and DENIES becomes a `reason` (all such reasons are kept — co-equal denies each block independently). A memo on a rule that FAILS but would ALLOW becomes a `remedy` — but only while the accumulated bit is not yet `certain` (`allow`/`deny`/`mixed`), so a remedy is suppressed once an earlier rule already settles the outcome. On `NEED_ROW_DATA` (rec absent) the accumulator is deliberately NOT advanced, preserving later remedies rather than suppressing on a shadow we can't confirm; on any other exception a synthetic `reason` memo naming the failing formula is pushed for every bit. `MemoInfo._processRule` then merges the lower-precedence default's memos but keeps only its `reason`s when this rule set's permission for a bit is already certain — because a shadowed remedy would be misleading (satisfying it wouldn't change the outcome), while a `reason` still names a real co-equal barrier.
**Invariant:** memos are only surfaced for DENIED bits; a memo on an allowed bit is never shown. `reason` = a rule that passes and denies; `remedy` = a rule that fails but would allow. A remedy is dropped when a higher-precedence rule certainly denies/decides the bit; reasons are never dropped (several rules can independently block). The `NEED_ROW_DATA` branch keeps `acc` unadvanced so remedies aren't suppressed on an unconfirmable shadow — on the row path (where memos actually show) `rec` is present anyway.
**Probe:** `test/server/lib/GranularAccess.ts` — "reports memos sensibly" (:906+) pins reason/remedy semantics; the "forces a row check for rules with memo and rec" suite (:239-460) pins the denySome→mixed conversion that makes memo attribution possible.
**Coverage caveat:** the shadowed-remedy drop path (default-memo filtering on a certain bit) is exercised indirectly through the memo suites; no isolated unit test isolates `mergeMemoSets` dedup.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "MemoInfo extractMemos mergeMemoSets isCertainPermission", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the reason/remedy two-kind memo model with the shadowed-remedy drop (keep only `reason`s from lower-precedence defaults once a bit is certain), the co-equal-reasons-kept rule, and the `NEED_ROW_DATA`-preserves-accumulator behavior; adapt the memo text source (Grist pulls it from a formula comment) and the permission-prop vocabulary; omit the formula-comment extraction if your engine stores memos separately.
