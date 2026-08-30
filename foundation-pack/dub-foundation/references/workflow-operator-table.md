<!-- capsule-v2 -->
# Workflow operator table — how do you make condition operators self-validating AND self-evaluating from one definition?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1` (operator table reworked in the drift window). **Question:** Where should operator validation and evaluation logic live so the API, the cron evaluator, and the zod schema can never disagree?

## WORKFLOW_OPERATORS: one object per operator, both halves attached
**Path/Symbol:** `apps/web/lib/api/workflows/operator-definitions.ts:WORKFLOW_OPERATORS` (:17-196).
**Signature:** `type WorkflowOperator = { name, label, validate(value): void, evaluate(attributeValue: number|string, conditionValue: ConditionValue): boolean }` — `validate` THROWS user-facing errors; `evaluate` returns false on any type mismatch (never throws).
**Data Shape:** `ConditionValue = number | { min?: number; max?: number } | string | string[]`; keys are the wire enum (`gte`, `lte`, `between`, `eq`, `ne`, `in`, `notIn`) exported as `WORKFLOW_OPERATOR_KEYS`.

### Decisive source
```ts
gte: {
  name: "gte", label: "is at least",
  validate(value) { if (typeof value !== "number" || isNaN(value) || value < 0)
    throw new Error("Please enter a value greater than or equal to 0."); },
  evaluate(attributeValue, conditionValue) {
    if (typeof attributeValue !== "number" || typeof conditionValue !== "number") return false;
    return attributeValue >= conditionValue;   // type mismatch = false, NOT throw
  },
},
```

**Flow:** creation-time — zod's `workflowConditionSchema.superRefine` calls `operatorDefinition.validate(data.value)` to convert throws into per-field issues; API-time — `validateWorkflowConditions`/`checkWorkflowConditions` re-run validate per condition for human-numbered errors; run-time — `evaluateWorkflowConditions` walks conditions and calls `evaluate(attributeValue, condition.value)`, treating unknown operators / missing context values / nulls as hard FALSE with a console error.
**Invariant:** the two failure postures are deliberately different — validate is loud (throws → 400 with message), evaluate is silent-false (a workflow whose data drifted simply doesn't fire; an evaluation error must never crash a fan-out loop). Numeric operators guard `isNaN` + negativity at BOTH layers; `between` requires `max > min > 0`; list ops require non-empty all-string arrays. Any new operator must implement both methods or the schema/evaluator pair drifts apart. The attribute side separately constrains WHICH operators apply (`attributeDefinition.operators` allowlist checked before validate).
**Probe:** `tests/workflows/comparison-operators.test.ts` (224L) pins gte/lte/between `evaluate` (type-mismatch ⇒ false, inclusive bounds, `{min:1}`-only ⇒ false) AND `validate` throw messages directly (:6-80+); `playwright/api/campaigns/send-campaign-workflow.spec.ts` exercises gte/lte end-to-end. Deterministic probe: POSTing `{attribute:"totalLeads", operator:"between", value:{min:5,max:1}}` ⇒ 400 "Maximum value must be greater than minimum value."
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "WORKFLOW_OPERATORS evaluate validate", limit: 8 });
// → lib.api.workflows.operator-definitions.WORKFLOW_OPERATORS @ operator-definitions.ts 17-196
```

## Verdict
Adopt the co-located validate/evaluate operator record and the loud-validate vs silent-false-evaluate split for any user-defined rule engine. Adapt the value union to your domain types. Omit operators your UI can't express.
