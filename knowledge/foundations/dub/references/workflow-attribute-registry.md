<!-- capsule-v2 -->
# Workflow attribute registry — how do you declare which attributes exist, which operators they accept, and what data each one needs fetching?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1` (drift pass; `WORKFLOW_TYPE_ATTRIBUTES` + per-type schema files are new since `873edc5a`). **Question:** How does a rule engine know an attribute's allowed operators and its data-fetching cost BEFORE it evaluates anything?

## WORKFLOW_ATTRIBUTES → type-specific overlays → data requirements
**Path/Symbol:** `apps/web/lib/api/workflows/attribute-definitions.ts:WORKFLOW_ATTRIBUTES` (:36-91, type at :13); overlays in `workflow-type-attributes.ts:WORKFLOW_TYPE_ATTRIBUTES` and `send-campaign/schema.ts:SEND_CAMPAIGN_ATTRIBUTES` (:35+); requirement fan-out in `utils.ts:getWorkflowDataRequirements` (:36-59).
**Signature:** `WorkflowAttribute = { name, label, inputType: "number"|"currency"|"dropdown"|"none"|"group", operators: readonly string[], requires: readonly WorkflowDataRequirement[], dropdownValues?, exclusive?, scheduled? }`; `getWorkflowDataRequirements({ conditions }): Record<"commissions"|"partnerLinkStats", boolean>`.
**Data Shape:** seven canonical keys (`totalLeads, totalConversions, totalSaleAmount, totalCommissions, partnerEnrolledDays, partnerJoined, partnerGroup`); overlays SPREAD the base definition and narrow operators (`...WORKFLOW_ATTRIBUTES.totalLeads, operators: ["lte","gte"] as const`) so the wire enum stays the superset while each workflow type sees a subset.

### Decisive source
```ts
// attribute-definitions.ts — cost lives ON the definition:
totalCommissions: { name: "totalCommissions", label: "total commissions",
  inputType: "currency", operators: ["gte"], requires: ["commissions"] },
partnerJoined: { ..., inputType: "none", operators: ["gte"],
  requires: [], exclusive: true },
// send-campaign/schema.ts — per-type operator narrowing by spread:
const SEND_CAMPAIGN_METRIC_ATTRIBUTES = {
  totalLeads: { ...WORKFLOW_ATTRIBUTES.totalLeads, operators: ["lte","gte"] as const }, ... };
// utils.ts — fetch planning from conditions alone:
export function getWorkflowDataRequirements({ conditions }) {
  const requirements = new Set<WorkflowDataRequirement>();
  for (const condition of conditions) {
    const attribute = WORKFLOW_ATTRIBUTES[condition.attribute];
    if (!attribute) continue;
    for (const requirement of attribute.requires) requirements.add(requirement);
  }
  return { commissions: requirements.has("commissions"),
           partnerLinkStats: requirements.has("partnerLinkStats") };
}
```

**Flow:** UI/schema derive their enums from the same registry (`z.enum(WORKFLOW_ATTRIBUTE_KEYS)`) → API validation checks `attributeDefinition.operators.includes(condition.operator)` before value validation → executors consult `requires` to decide whether to run the expensive commission aggregate or link-stats query AT ALL (executeWorkflows: `shouldFetchCommissions = parsedWorkflows.some(...)`), and `inputType === "none"` marks value-less event attributes (`partnerJoined`) that skip value validation entirely.
**Invariant:** the registry is the single source of truth for THREE consumers (schema enums, operator allowlists, fetch planning) — adding an attribute without its `requires` silently makes evaluators see null and fail closed; narrowing operators via spread must keep the SAME keys so `WORKFLOW_ATTRIBUTE_KEYS` stays a valid z.enum. `exclusive: true` (partnerJoined) means sole-condition-only and is enforced in validate-workflow-conditions + `satisfiesExclusiveAttributeRules`.
**Probe:** `tests/workflows/award-bounty-workflow.test.ts:20-30` creates a bounty with `performanceCondition {attribute:"totalLeads", operator:"gte", value:1}` and the workflow fires on reaching goal — pins registry-driven evaluation end-to-end. Deterministic probe: `getWorkflowDataRequirements({conditions:[{attribute:"totalCommissions"}]})` ⇒ `{commissions:true, partnerLinkStats:false}`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "WORKFLOW_TYPE_ATTRIBUTES getWorkflowDataRequirements", limit: 8 });
// → lib.api.workflows.workflow-type-attributes.WORKFLOW_TYPE_ATTRIBUTES; utils.getWorkflowDataRequirements
```

## Verdict
Adopt the declarative attribute record carrying operators + data-cost + exclusivity, and derive schemas/validation/fetch-planning from it. Adapt requirement kinds to your expensive sources. Omit per-type overlays until a second workflow type exists.
