<!-- capsule-v2 -->
# Condition validation vs evaluation — why does creation-time check collect errors while run-time check returns false?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** What is the division of labor between the two condition walkers, and which failure posture belongs to each so a porter doesn't merge them?

## checkWorkflowConditions: numbered error collector (API surface)
**Path/Symbol:** `apps/web/lib/api/workflows/check-workflow-conditions.ts:checkWorkflowConditions` (:8-92).
**Signature:** `checkWorkflowConditions({ conditions?: WorkflowCondition[] | null, workflowType: WorkflowType }): { valid: boolean; errors: string[] }` — never throws.
**Data Shape:** looks conditions up in the PER-TYPE overlay `WORKFLOW_TYPE_ATTRIBUTES[workflowType]` (from `workflow-type-attributes.ts`, :11-18), not the superset table.

### Decisive source
```ts
if (!conditions || conditions.length === 0) return { valid: true, errors: [] };
// ...
if (!attributeDefinition) { errors.push(`Condition ${conditionIndex + 1}: Invalid activity.`); continue; }
// ...
if (!(attributeDefinition.operators as readonly string[]).includes(condition.operator)) {
  const operatorLabel = operatorDefinition.label ?? condition.operator;
  errors.push(`Operator "${operatorLabel}" is not valid for the activity "${condition.attribute}".`);
  continue;
}
// Attributes with inputType "none" (e.g. partnerJoined) don't require a value.
if (attributeDefinition.inputType === "none") continue;
```
(:18-23 empty-valid gate; operator-allowlist at :55-65; inputType none at :67-70)

**Flow:** empty ⇒ valid (:18-23) · per condition: missing attribute → numbered human message · unknown attribute for THIS workflow type → invalid activity · unknown operator → invalid operator · operator not in the attribute's allowlist → labeled mismatch error using the OPERATOR's label · `inputType: "none"` attributes skip value checks entirely · null value → "Please enter a value." · finally `operatorDefinition.validate(value)` with its throw converted into an error string (:77-85).
**Invariant:** validation is scoped to the WORKFLOW TYPE's attribute overlay — a condition legal for moveGroup (`between`) is invalid for awardBounty even though both live in the superset registry. Errors carry 1-based condition numbers because they render in a UI list. Empty conditions are VALID here (a workflow may be unconditional); the evaluator makes the opposite choice deliberately.
**Probe:** deterministic probe: `grep -c 'Condition ${conditionIndex + 1}' apps/web/lib/api/workflows/check-workflow-conditions.ts` = 5 (:34, :43, :51, :73, :81 — four pushes plus one interpolated message); direct behavior pinned by `playwright/api/campaigns/send-campaign-workflow.spec.ts` 400-shapes on campaign creation. Coverage caveat: no vitest unit pins this file directly.

## evaluateWorkflowConditions: silent-false predicate (run-time)
**Path/Symbol:** `apps/web/lib/api/workflows/evaluate-workflow-conditions.ts:evaluateWorkflowConditions` (:7-47).
**Signature:** `evaluateWorkflowConditions({ conditions: WorkflowCondition[], context: Partial<Record<WorkflowAttributeKey, number | string | null>> }): boolean`.
**Data Shape:** context values come pre-aggregated from callers (orchestrator or action executors); the evaluator does NO fetching.

### Decisive source
```ts
if (conditions.length === 0) return false;   // NOT true — opposite of the API checker
for (const condition of conditions) {
  const operator = WORKFLOW_OPERATORS[condition.operator];
  if (!operator) return false;               // console.error + hard FALSE
  const attributeValue = context[condition.attribute];
  if (attributeValue == null) return false;  // null/undefined attribute = no fire
```
(:14 empty-false; :24-26 unknown operator; :31-34 missing attribute)

**Flow:** every anomaly (unknown operator, absent/null context value, null condition value, any operator evaluate false) logs to console and returns false immediately; only a full AND-pass over all conditions returns true.
**Invariant:** the two functions are intentionally asymmetric on the empty case — creation-time treats "no conditions" as valid config, run-time treats it as "never fire" (an unconditional workflow would otherwise execute on EVERY event of its trigger type). Run-time failures must never throw: they happen inside fan-out loops where an exception would abort sibling workflows. Note `partnerJoined` (inputType none, exclusive) is evaluated via the caller stuffing a numeric sentinel (`daysSinceEnrollment`) into the context under that key.
**Probe:** `tests/workflows/comparison-operators.test.ts` pins each operator's evaluate/validate semantics (:6-80+); the false-on-empty contract is pinned indirectly by `tests/workflows/move-group-workflow.test.ts` "Workflow doesn't execute when conditions are not met" (:225-291). Deterministic probe: `grep -n 'conditions.length === 0) return false' apps/web/lib/api/workflows/evaluate-workflow-conditions.ts` = line 14.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "evaluateWorkflowConditions", limit: 5 });
// → dub.apps.web.lib.api.workflows.evaluate-workflow-conditions.evaluateWorkflowConditions @ evaluate-workflow-conditions.ts 7-47
```

## Verdict
Adopt the split posture: loud collected-errors checker bound to the per-type overlay for the API; silent-false pure predicate for the engine, including the empty-conditions asymmetry. Adapt error wording/context sources. Omit the local-dev pretty-print logging branch.
