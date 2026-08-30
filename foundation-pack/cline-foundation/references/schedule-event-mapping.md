<!-- capsule-v2 -->
# Schedule event mapping — how do command replies and internal execution outcomes project onto hub events without leaking reads or failures?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** which schedule operations publish hub events, gated by what, and how do the two trigger variants differ in what they return?

## Two ok-gated projection tables
**Path/Symbol:** `sdk/packages/core/src/hub/server/hub-schedule-events.ts:3-20` (`eventNameForScheduleCommand`, 20 lines whole); publication site `hub-server-transport.ts:853-865` (default dispatch branch); internal-outcome filter `hub-server-transport.ts:307-325` (ctor `eventPublisher`); trigger twins `cron/service/schedule-service.ts:353-370`.
**Signature:** `eventNameForScheduleCommand(command): HubEventEnvelope["event"] | undefined`; `eventPublisher(eventType, payload)` injected into HubScheduleService.
**Data Shape:** five mutating commands map to events; everything else maps `undefined`. Internal outcomes use dot-form names filtered to underscore-form hub events.

### Decisive source
```ts
// table 1 — command → event (transport default branch, ok-gated):
default: {
    const reply = await this.scheduleCommands.handleCommand(envelope, authority);
    if (reply.ok) {
        const event = eventNameForScheduleCommand(envelope.command);
        if (event) this.publish(buildHubEvent(event, reply.payload));  // payload verbatim
    }
    return reply;
}
// create→schedule.created; update/enable/disable→schedule.updated;
// delete→schedule.deleted; trigger→schedule.triggered
```
```ts
// table 2 — internal execution outcome → event (ctor filter):
const mapped =
    eventType === "schedule.execution.completed" ? "schedule.execution_completed" :
    eventType === "schedule.execution.failed"    ? "schedule.execution_failed"    :
    undefined;
if (!mapped) return;   // every other internal outcome is silently dropped
// trigger twins:
await triggerScheduleNow(id)      // enqueue → await runner.tick() → re-read run from store → terminal record
triggerScheduleNowDetached(id)    // enqueue → void runner.tick().catch(()=>{}) → merely-enqueued record
```

**Flow:** agenda `task.*` commands delegate FIRST after the drain gate (:714-716), so they never reach this default branch; any unknown command falls INTO HubScheduleCommandService whose own default answers `unsupported_command` — meaning the catch-all router treats schedule as the last-resort namespace. Reads (`list/get/stats/list_executions/active/upcoming`) map undefined and NEVER publish, even on success.
**Invariant:** publication is double-gated — reply.ok AND a non-undefined mapping — so failed mutations and pure reads stay silent while success payloads are forwarded verbatim. The awaited/detached twin pair moves the await choice to the CALLER: `payload.wait === false` selects detached (:121-131), returning the enqueued run instead of blocking on the full session.
**Probe:** `schedule-service.test.ts`: "creates, triggers, and reports schedule history" (:43-115) pins `publishedEvents` equaling exactly one `{eventType:"schedule.execution.completed", payload:{scheduleId, executionId, sessionId:"session-1", status:"success"}}` and `created.mode === "yolo"`; "publishes failed schedule execution events" (:169-220) pins the `_failed` twin with `errorMessage:"runtime failed"`. Vertical slice `agenda-task-hub.test.ts` :311-319 asserts the event array contains `schedule.created`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "cline", query: "eventNameForScheduleCommand schedule created updated deleted triggered", limit: 8 });
```

## Verdict
Adopt ok-gated reply→event projection tables at the router boundary and a separate allow-list for internal outcomes when you bridge a scheduler to an event bus. Adapt event names to your vocabulary but keep reads silent and failures explicit-only. Adopt the awaited/detached twin naming pattern whenever one API must serve both interactive and fire-and-forget callers. Runner caveat recorded honestly (no node_modules).
