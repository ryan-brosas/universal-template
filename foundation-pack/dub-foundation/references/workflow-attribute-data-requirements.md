<!-- capsule-v2 -->
# Attribute registry & data requirements — how do condition attributes declare their own fetch cost?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** How should a rule engine's attribute catalog be structured so query planning (what data to load) derives from the same definitions the UI and validators use?

## WORKFLOW_ATTRIBUTES: superset table with requires/scheduled/exclusive flags
**Path/Symbol:** `apps/web/lib/api/workflows/attribute-definitions.ts:WORKFLOW_ATTRIBUTES` (:36-92) + `getWorkflowDataRequirements` in `apps/web/lib/api/workflows/utils.ts` (:36-59).
**Signature:** `WorkflowAttribute = { name, label, inputType: "number"|"currency"|"dropdown"|"none"|"group", operators: readonly string[], requires: readonly WorkflowDataRequirement[], dropdownValues?, exclusive?, scheduled? }`; `WORKFLOW_DATA_REQUIREMENTS = ["commissions", "partnerLinkStats"]`.
**Data Shape:** seven attribute keys (`totalLeads`, `totalConversions`, `totalSaleAmount`, `totalCommissions`, `partnerEnrolledDays`, `partnerJoined`, `partnerGroup`); module header forbids UI imports — per-type overlays live in the workflow schemas instead.

### Decisive source
```ts
partnerGroup: {
  name: "partnerGroup", label: "group",
  inputType: "group",
  operators: ["eq", "ne", "in", "notIn"],
  requires: [],
},
// utils.ts — fetch planning from the same registry:
for (const requirement of attribute.requires) requirements.add(requirement);
return {
  commissions: requirements.has("commissions"),
  partnerLinkStats: requirements.has("partnerLinkStats"),
};
```
(attribute-definitions.ts :85-92; utils.ts :50-58)

**Flow:** schema/UI derive value widgets + operator menus from these records · API validation walks them via the per-type overlays · orchestrator/executors call `getWorkflowDataRequirements(conditions)` to decide whether to run the commission aggregate or load link stats · `scheduled: true` on `partnerEnrolledDays` routes it to the 12h cron instead of event triggers (`isScheduledWorkflow` in utils.ts :20-34) · `exclusive: true` on `partnerJoined` is enforced by `satisfiesExclusiveAttributeRules` (:81-121): an exclusive attribute must appear ALONE — any pairing with other used-attributes returns false symmetrically.
**Invariant:** the registry is the single planning truth: adding a new attribute with `requires: ["commissions"]` automatically makes both the single-partner aggregate and the groupBy path fetch commissions for workflows using it — a porter who hardcodes "always fetch X" breaks the lazy-aggregate economics. `inputType: "none"` doubles as "no value required" at validation. The superset/overlay split means type-level narrowing (operators, key sets) never mutates the shared definitions.
**Probe:** `tests/workflows/find-groups-with-matching-rules.test.ts` exercises group-attribute matching built on these keys; deterministic probe: `grep -c 'requires: \[' apps/web/lib/api/workflows/attribute-definitions.ts` = 7.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "getWorkflowDataRequirements", limit: 5 });
// → dub.apps.web.lib.api.workflows.utils.getWorkflowDataRequirements @ utils.ts 36-59
```

## Verdict
Adopt declarative `requires` on attribute definitions driving fetch planning, the scheduled/exclusive flags as first-class routing metadata, and the superset+per-type-overlay layering. Adapt requirement kinds to your data plane. Omit dub's specific attribute set.
