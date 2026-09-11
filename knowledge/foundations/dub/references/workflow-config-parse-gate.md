<!-- capsule-v2 -->
# Workflow config parse gate — why does the stored JSON get re-validated on every execution?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** What contract must a stored-workflow parser satisfy so corrupt DB rows can never crash or mis-fire an automation engine?

## parseWorkflowConfig: parse both arrays, demand non-empty, return first action only
**Path/Symbol:** `apps/web/lib/api/workflows/parse-workflow-config.ts:parseWorkflowConfig` (:8-31).
**Signature:** `parseWorkflowConfig(workflow: Pick<Workflow, "id" | "triggerConditions" | "actions">): { conditions: WorkflowCondition[]; action: WorkflowAction }` — THROWS on invalid shape or empty arrays.
**Data Shape:** `triggerConditions` / `actions` are raw JSON columns; parsed through `z.array(workflowConditionSchema)` and `z.array(workflowActionSchema)` (a discriminated union on `type`: awardBounty/sendCampaign/moveGroup).

### Decisive source
```ts
const conditions = z.array(workflowConditionSchema).parse(workflow.triggerConditions);
const actions = z.array(workflowActionSchema).parse(workflow.actions);

if (conditions.length === 0) {
  throw new Error(`[Workflows] No conditions found in workflow ${workflow.id}.`);
}
if (actions.length === 0) {
  throw new Error(`[Workflows] No actions found in workflow ${workflow.id}.`);
}

return {
  conditions,
  action: actions[0],   // FIRST action only — multi-action configs are silently truncated
};
```
(:11-30)

**Flow:** every consumer (orchestrator :91, and all three action executors via their own `parseWorkflowConfig(workflow)` call) re-parses the SAME JSON columns at execution time · throws bubble to the orchestrator's per-row catch (silent skip) or to a handler's own guard (`action.type !== X → return`) when invoked directly.
**Invariant:** (1) DB JSON is NEVER trusted as typed data — schema evolution or manual edits cannot inject malformed conditions into the engine; (2) empty conditions/actions are loud errors at this layer even though `evaluateWorkflowConditions` treats empty as false — this is the guard that makes the evaluator's empty-false case unreachable from persisted workflows; (3) exactly ONE action executes per workflow (`actions[0]`): the UI writes single-action rows, so extra entries would be silently ignored rather than fanned out. A porter who "fixes" this into executing all actions changes fan-out semantics.
**Probe:** deterministic probe: `grep -c 'No conditions found in workflow\|No actions found in workflow' apps/web/lib/api/workflows/parse-workflow-config.ts` = 2; behavior exercised by every move-group/bounty/campaign test through the shared funnel (e.g. `tests/workflows/move-group-workflow.test.ts` asserts the persisted row parses back with one action + one condition, :69-81).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "parseWorkflowConfig", limit: 5 });
// → dub.apps.web.lib.api.workflows.parse-workflow-config.parseWorkflowConfig @ parse-workflow-config.ts 8-31
```

## Verdict
Adopt re-parse-at-execution-time over trusting stored JSON, the non-empty throw, and the first-action-only truncation (or make multi-action explicit if you port it). Adapt the zod schemas. Omit nothing else — this is a deliberately tiny seam.
