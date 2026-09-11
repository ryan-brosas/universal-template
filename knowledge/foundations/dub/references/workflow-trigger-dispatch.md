<!-- capsule-v2 -->
# Workflow trigger dispatch — how does one event fan out to many user-defined workflows without one failure poisoning the rest?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** Where should trigger-event routing, data prefiltering, and per-workflow error isolation live so a fan-out engine can be ported without turning one bad workflow into a dropped event?

## executeWorkflows: prefilter → parse-filter → lazy aggregate → isolated handlers → flush
**Path/Symbol:** `apps/web/lib/api/workflows/execute-workflows.ts:executeWorkflows` (:44-242).
**Signature:** `executeWorkflows({ event: WorkflowTriggerEvent, identity: WorkflowIdentity, metrics?: { current?, aggregated? } }): Promise<void>` — returns void; NEVER throws to callers.
**Data Shape:** `EVENT_ATTRIBUTES: Record<WorkflowTriggerEvent, WorkflowAttributeKey[]>` maps each trigger to the attribute names it can affect (`partnerEnrolled→[partnerJoined]`, `leadRecorded→[totalLeads, partnerGroup]`, `saleRecorded→[totalConversions, totalSaleAmount, partnerGroup]`, `commissionRecorded→[totalCommissions, partnerGroup]`) (:37-42). Workflows are Prisma rows with JSON `triggerConditions` / `actions`.

### Decisive source
```ts
const workflows = await prisma.workflow.findMany({
  where: {
    programId,
    disabledAt: null,
    OR: attributes.map((attribute) => ({
      triggerConditions: {
        path: "$[*].attribute",            // JSON path over the conditions ARRAY
        array_contains: attribute,
      },
    })),
  },
});
// ...parse each row; a row that fails zod is DROPPED silently:
} catch (error) { return null; }
// Commissions require a separate expensive aggregate query.
// We only fetch if needed:
const shouldFetchCommissions = parsedWorkflows.some(({ config }) =>
  config.conditions.some((c) => c.attribute === "totalCommissions"));
```
(:66-77 parse-drop at :86-104, lazy gate at :111-115)

**Flow:** map event → eligible attributes (:59) · empty ⇒ return before any query (:61-64) · SQL prefilter by JSON-path membership so disabled/wrong-attribute workflows never leave the DB (:66-77) · per-row zod parse with silent skip of corrupt configs (:86-109) · ONE enrollment fetch (with per-link stat columns + tag ids) beside a CONDITIONAL commission `_sum` aggregate resolved via `Promise.resolve({_sum:{earnings:null}})` placeholder when no workflow needs it (:113-168) · hard-stop when enrollment missing or has no groupId (:170-182) · build the enriched context (`metrics.aggregated.{leads,conversions,saleAmount,commissions}` from `aggregatePartnerLinksStats`, commissions defaulting `?? 0`) (:184-210) · sequential handler loop where EVERY throw is caught, logged to axiom with `workflows.execute_failed` + correlation, and the loop CONTINUES (:212-239) · `await logger.flush()` before returning (:241).
**Invariant:** (1) an event is never lost because one workflow's config is corrupt — parse failures are skipped rows, not exceptions; (2) one workflow's execution failure never blocks later workflows — catch-and-continue inside the loop; (3) the expensive commission aggregate runs at most once per event and only when some surviving condition references `totalCommissions`; (4) log flush happens even though errors were swallowed, so observability never trails into the next invocation.
**Probe:** `tests/workflows/move-group-workflow.test.ts` "Disabled workflow doesn't execute partner move" (:144-227) pins the `disabledAt: null` prefilter end-to-end (partner stays in source group); deterministic probe: `grep -c 'array_contains' apps/web/lib/api/workflows/execute-workflows.ts` = 1.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "executeWorkflows", limit: 5 });
// → dub.apps.web.lib.api.workflows.execute-workflows.executeWorkflows @ execute-workflows.ts 44-242
```

## Verdict
Adopt the three-layer funnel (SQL JSON-path prefilter → parse-and-skip → catch-and-continue loop) plus the lazy-aggregate pattern keyed off surviving conditions. Adapt the attribute→event table and Prisma JSON-path syntax to your store. Omit dub's console.log noise; keep the flush-before-return if your logger batches.
