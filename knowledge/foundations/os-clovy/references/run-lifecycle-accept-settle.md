<!-- capsule-v2 -->
# Run lifecycle accept-then-settle — what exactly does the host see between run.start and a terminal event?

**Source:** os-clovy MIT `main@8fed7acb51622d36bfaaa056f43931015dfd5d72`; Codebase Memory `os-clovy`. **Question:** A porter building an RPC-hosted agent service must decide when run.start responds, how steering/cancel interact with in-flight work, and which event sequence each outcome emits.

## RuntimeService run FSM
**Path/Symbol:** `agent-runtime/src/service.ts:RuntimeService.start` (:85-100), `startAcceptedRun` (:102-158), `steer` (:185-199), `cancel` (:201-206), `settle` (:273-320), helpers `runKey` (:378-380), `validateRunStart` (:365-376).
**Signature:** `handle(request): Promise<JsonValue>`; active runs keyed `${sessionId}\u0000${runId}` → `{controller, steering[], steeringIds}`.
**Data Shape:** start/resume return `{accepted:true}` synchronously or throw `-32002 "Run is already active"`; steering returns `{accepted:false, reason:"not_active"}` | `{accepted:true, duplicate?:true}`.

### Decisive source
```ts
this.activeRuns.set(runKey(sessionId, runId), active);
setImmediate(() => { void this.settle(sessionId, runId,
  this.startAcceptedRun(sessionId, runId, parsed, active)); });
return { accepted: true };            // host acknowledged BEFORE any event fires

// steer: dedupe by messageId BEFORE queueing
if (active.steeringIds.has(messageId)) return { accepted: true, duplicate: true };
// drain at the next MODEL boundary inside the provider:
takeSteering: () => active.steering.splice(0)

// settle outcome algebra (finally: activeRuns.delete):
aborted signal (even with a good result) → emit("run.cancelled", { history })
interruptions.length > 0  → emitUsage FIRST, then per-interruption
                            interruption.requested{...i, serializedState, usage}
finalOutput !== undefined → message.completed{text} → usage.updated → run.completed
error                     → aborted? run.cancelled{} : run.failed{error,category,code,retryable}
```

**Flow:** validate params → claim run key → accept → deferred work runs identity gate → compaction → `run.started{compacted,removedItemIds,contextSummary?}` → engine stream events forwarded verbatim → settle picks ONE terminal shape. Shutdown flips `shuttingDown` (all further methods except shutdown get `-32003`) and aborts every active controller.
**Invariant:** Exactly one terminal event per run; acceptance is never delayed by model/summary latency (a blocked summarizer still leaves `run.started` unemitted but the RPC reply already returned); cancel during pending summarize aborts the summary signal and yields exactly one `run.cancelled` with zero `run.started`; steering accepted only while the run key exists, consumed exactly once.
**Probe:** `agent-runtime/test/service.test.ts` — "streams lifecycle events ... in monotonic order" (sequence 1..5), "accepts before summarizing and cancels without starting a run", "queues a live steer for the active model boundary and rejects it after settlement". Suite runner-blocked at pin (`@openai/agents` import); test names/ranges read directly as Probe anchors.

## Get live surrounding code
**Retrieve:** executed at pin (top hits = target family):
```
search_graph({ project:"os-clovy", query:"run start accepted settle steering cancel active runs", file_pattern:"agent-runtime/*" })
→ src.service.RuntimeService.startAcceptedRun Method service.ts 102-158  (rank 1)
   src.service.RuntimeService.settle Method service.ts 273-320
   src.service.RuntimeService.start Method service.ts 85-100
```

## Verdict
Adopt synchronous-accept + deferred-execution, messageId-deduped steering drained at model boundaries, and the settle algebra (especially usage-before-interruption so a resumed Auto run keeps its concrete model). Adapt the event method names to your protocol. Omit the `\u0000`-joined runKey only if you have a structured map key — never use plain string concat without a separator (collision risk).
