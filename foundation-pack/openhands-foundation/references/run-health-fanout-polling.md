<!-- capsule-v2 -->
# Run-health fan-out polling — N-way latest-run dashboards that bound aggregate request rate and degrade to "unknown"

**Source:** OpenHands / All-Hands-AI MIT `main@8511fff62d3084587cda1add483fe5ea9c8bfd7e`; Codebase Memory `openhands`. **Question:** When a dashboard shows the last-run health of EVERY automation, how do you poll one-request-per-item without hammering the backend, and map run statuses to honest UI states?

## Connected graph-selected seam
**Path/Symbol:** `src/hooks/query/use-latest-automation-runs.ts` (96 L): `useLatestAutomationRuns` (42–96) with `IN_FLIGHT_POLL_INTERVAL_MS = 15_000` (:19) and `AUTOMATION_RUN_ACTIVITY_LIMIT = 12` (:22); `src/components/features/home/featured-automations/automation-run-health.ts` (136 L): `deriveRunHealth` (17–34), `getRunHealthLabelKey` (36–49), `shortenAutomationErrorDetail` (108–114), `shouldShowAutomationErrorHovercard` (117–122), `getLastRunTimestamp` (130–136). Dispatch/invalidation partner: `src/api/automation-service/automation-service.api.ts:AutomationService.dispatchAutomation` (428–443). No dedicated direct test for these two files — indirect coverage only via `__tests__/components/features/home/home-automation-run-tooltip.test.tsx` (recorded honestly).
**Signature:** `useLatestAutomationRuns(automations): Map<string, LatestAutomationRunState>`; `deriveRunHealth(state): "success"|"failed"|"in_progress"|"none"|"unknown"`; `shortenAutomationErrorDetail(detail): string`.
**Data Shape:** `LatestAutomationRunState { latestRun|null, recentRuns[], total?, isLoading, isError }`; TanStack `useQueries` fan-out keyed `[...AUTOMATION_RUNS_QUERY_KEY, id, {limit,offset}, backendId, orgId]`.

### Decisive source
```ts
// Status mapping is query-state-aware and FORWARD-compatible:
if (state.isLoading || state.isError) return "unknown";   // degraded, not failed
if (!state.latestRun) return "none";
switch (state.latestRun.status) {
  case COMPLETED: return "success";
  case FAILED:    return "failed";
  case PENDING: case RUNNING: return "in_progress";
  default: return "unknown";   // CANCELLED/SKIPPED + any status added later server-side
}
// Poll cadence is a rate-budget decision (doc-comment verbatim):
// detail page polls ONE automation at 3s; this hook fans out one request PER automation,
// so 15s makes a fully in-flight home section cost about the same as one open detail page.
refetchInterval: (query) => {
  const latest = query.state.data?.runs[0];
  return (latest?.status === PENDING || latest?.status === RUNNING) ? 15_000 : false;   // terminal => stop
},
retry: false,                 // settle into "unknown" instead of hammering an unhealthy service
refetchOnWindowFocus: false,  // mount already fans out N requests; focus refetch buys no health delta
staleTime: 60 * 1000,
// Backend leaves started_at unset (epoch/zero) while PENDING — guard it:
const time = new Date(candidate).getTime();
if (Number.isNaN(time) || time === 0) return null;
```

**Flow:** home section renders one chip per automation → each gets its own query sharing the runs key-prefix with the detail page, so `dispatchAutomation` mutations invalidate BOTH surfaces at once → while the newest run is non-terminal the query self-polls at the slow cadence and stops on terminal → `deriveRunHealth` folds query state + status into five UI words → errors render as first-sentence ≤48-char inline previews with hovercard overflow.

**Invariant:** Aggregate request rate is budgeted against the single-view baseline (N×15 s ≈ 1×3 s), never per-item fast polling; unknown-vs-failed is preserved (a broken poller is not a broken automation); every future backend status lands on "unknown", never crashes the switch; timestamps from lazy backends are NaN/0-guarded.

**Probe:** No runner execution possible for React hooks this pass (vitest blocked — no node_modules, clean read-only tree; no dedicated unit test exists for either file). Executed instead: full-file reads at HEAD, line-pinned content checks of every excerpt above, coverage check `no_recorded_issue` on both files, and MCP retrieval executed live (`search_graph` "dispatch automation trigger cron" → dispatchAutomation 428–443, run-health helpers 60–99).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openhands", query: "dispatch automation trigger cron", limit: 12 });
// executed this pass -> AutomationService.dispatchAutomation 428-443, deriveRunHealth family in
// src/components/features/home/featured-automations/automation-run-health.ts, use-latest-automation-runs.ts
```

## Verdict
Adopt the rate-budgeted conditional-poll pattern for any N-card live dashboard (poll only non-terminal rows; stop on terminal; retry:false into an explicit "unknown" state), plus the forward-compatible default-case status fold. Adapt intervals to your SLA and the status enum to your domain. Omit OpenHands' trigger-label/i18n surface. Caveat carried in the leaf: this seam has no dedicated upstream test — evidence here is source+graph only.
