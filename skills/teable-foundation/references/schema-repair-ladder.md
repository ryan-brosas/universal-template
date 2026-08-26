<!-- capsule-v2 -->
# Self-verifying repair ladder — why must a repairer re-validate after executing statements, and how do manual repairs gate on user confirmation?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** What is the exact decision ladder from "rule invalid" to "schema repaired", including dry-run and manual-repair branches?

## SchemaRepairer
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/schema/rules/repairer/SchemaRepairer.ts` — `repairInternal` (:117–388); hint resolution `rules/core/RuleRepairMetadata.ts` `getRuleRepairHint`; scoped batching :59–88.
**Signature:** `async *repairTable/Field/Rule(table, [fieldId, [ruleId]], options?: {dryRun?, manualRepairValues?, targetStatuses?}): AsyncGenerator<SchemaRepairResult>`; outcome enum `'repaired'|'unchanged'|'manual'|'skipped'`.
**Data Shape:** result carries `{status, outcome, message, details{missing,missingItems,extra,extraItems,statementCount,statements?}, repair}`; dry-run auto-repairs embed the COMPILED sql+parameters of every statement.

### Decisive source
```ts
// 1. validate → 2. replay up() → 3. RE-VALIDATE. Never trust statement success:
await executeScopedRepairStatements(ctx.db, ctx.metaDb, statements);
const revalidationResult = await rule.isValid(validationCtx);
if (!revalidationResult.value.valid) {
  yield { ...errorResult(pending, 'Repair executed but schema is still invalid', {...}),
          repair };
  repairedRules.set(rule.id, false);   // dependents will be skipped
  continue;
}

// manual gate: rule declares manual OR its hint says so with a form schema
const shouldUseManualRepair =
  rule.repairMode === 'manual' ||
  Boolean(repair?.mode === 'manual' && repair.manualRepairSchema);
if (shouldUseManualRepair && !options?.manualRepairValues) {
  yield { ...warnResult(pending, 'Rule requires manual repair', 'manual', details), repair };
  continue;                             // ← waits for user-supplied values
}
```

**Flow:** plan → per rule: dependency-gate on REPAIRED map (out-of-closure deps count as satisfied) → optional `targetStatuses` filter ('error' for required, 'warn' for optional) → already-valid⇒`unchanged` → manual branch: no values⇒warn 'manual', values+dryRun⇒success without executing, else run `rule.manualRepair(values,{dryRun})` then re-validate → auto branch: unavailable hint⇒skipped, zero statements⇒warn 'manual', dryRun⇒compile-only preview, execute→re-validate→`repaired`. Statements are batched into contiguous scope runs (data|meta) and dispatched to the right db.
**Invariant:** a rule counts as repaired ONLY when post-execution validation says valid — execution errors alone are not success; every terminal path records `repairedRules.set(rule.id, bool)` so dependent skipping stays truthful.
**Probe:** `packages/v2/adapter-table-repository-postgres/src/schema/rules/core/RuleRepairMetadata.spec.ts:148 'should skip statement generation during check-time hint computation'`, :171 'prefer the rule-provided repair hint', :193 'surface statement-generation failures as unavailable manual repair'.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "SchemaRepairer repairInternal manualRepairValues dryRun revalidationResult getRuleRepairHint", limit: 10 });
```

## Verdict
Adopt validate→execute→RE-validate as the repair contract, the four-outcome vocabulary, closure-relaxed dependency gating, contiguous-scope statement batching, and the form-schema-driven manual gate; adapt dry-run output shape to host CLI; omit Effect-TS service wrapper (devtools layer) around it.
