<!-- capsule-v2 -->
# Automation cache scope & prefix invalidation — how do TanStack mutations bust every page of a list without leaking another backend's cache?

**Source:** OpenHands / All-Hands-AI (MIT) `main@8511fff62d3084587cda1add483fe5ea9c8bfd7e`; Codebase Memory `openhands`. **Question:** How should query keys be scoped so switching backends refires fetches automatically, while invalidations still reach every pagination slice in one call?

## Scoped keys, prefix invalidations
**Path/Symbol:** `src/hooks/query/use-automations.ts` (`AUTOMATIONS_QUERY_KEY` :11, `useAutomations` :19–33, `useDispatchAutomation` :94–109).
**Signature:** `queryKey: [...AUTOMATIONS_QUERY_KEY, { limit, offset }, active.backend.id, active.orgId]`; `onSuccess: () => { invalidateQueries({ queryKey: AUTOMATIONS_QUERY_KEY }); … }`.
**Data Shape:** Read key = `["automations", {limit,offset}, backendId, orgId]`. Invalidation key = bare `["automations"]` (and `AUTOMATION_DETAIL_QUERY_KEY`, `[...AUTOMATION_RUNS_QUERY_KEY, id]` for dispatch/cancel).

### Decisive source
```ts
export const AUTOMATIONS_QUERY_KEY = ["automations"] as const;
// …
queryKey: [
  ...AUTOMATIONS_QUERY_KEY,
  { limit, offset },
  active.backend.id,
  active.orgId,
],
// …
onSuccess: (_run, id) => {
  queryClient.invalidateQueries({ queryKey: AUTOMATIONS_QUERY_KEY });
  queryClient.invalidateQueries({ queryKey: AUTOMATION_DETAIL_QUERY_KEY });
  queryClient.invalidateQueries({
    queryKey: [...AUTOMATION_RUNS_QUERY_KEY, id],
  });
```

**Flow:** mutation succeeds → invalidate the shared prefix → every live observer whose full key starts with that prefix (all pages, both backend scopes) refetches; a backend *switch* needs no invalidation at all because the key embeds `backend.id + orgId`, so the new selection is a brand-new cache entry.
**Invariant:** The two mechanisms are complementary and must not be conflated: scoping by backend prevents cross-backend cache reads; prefix invalidation reaches all pagination slices. Dropping `active.backend.id/orgId` from the read key leaks one backend's data into the other's UI; invalidating the fully-scoped key instead misses sibling pages.
**Probe:** `__tests__/hooks/query/use-automations-backend-switch.test.tsx:139-157` — flips the active backend with no explicit invalidate and asserts a second `getAutomations` fetch fires purely via key identity; `:206-252` pins runs polling engaging only while a run is non-terminal.

### Secondary invariants worth porting
- Analytics ride mutation success, not button clicks: `trackAutomationDisableButton` fires ONLY when `variables.enabled === false` (:45–47); every event carries `backendKind` captured at hook time.
- Detail/runs hooks share the same prefix family (`use-automation-detail` exports the constants), so one dispatch refreshes detail page AND home chips together — the pass-2 run-health capsule builds on this exact key contract.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openhands", query: "use-automations mutations invalidate automations query keys", limit: 10, fields: ["signature", "lines"] });
// → useAutomations :19-33, useDispatchAutomation :94-109, query-keys.byScope
```

## Verdict
Adopt "read key scoped by environment identity + invalidate on shared prefix" as a pair. Adapt key segments to your domain (tenant id / region instead of backend+org). Omit OpenHands' automation analytics events and the runs-polling specifics (covered separately). Coverage caveat: none recorded at pin; direct test read-at-HEAD (runner blocked).
