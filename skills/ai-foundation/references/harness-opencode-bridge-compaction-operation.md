<!-- capsule-v2 -->
# Opencode bridge compaction operation — how do you run a native summarize operation whose completion is an event, not an API return?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** The opencode bridge's `/compact` rail (host-side, pass-23) sends a start frame with `operation:'compact'`; the bridge must then trigger the runtime's native session summarize and report exactly one `compaction` event — but the summarize API call returns before the compaction actually finishes, and the finish signal arrives on the SSE event stream. How do you settle the operation honestly?

## Settle race over one deferred
**Path/Symbol:** `packages/harness-opencode/src/bridge/index.ts` — runTurn entry (:140–163, operation branch :148–149), `runCompaction` (:763–853), `legacySessionSummarize` (:445–456), `resolveCompactionModel` (:1393–1415), `modelRefFromAssistantSnapshot` (:1417–1427), `modelRefFromSessionInfo` (:1429–1433), `modelRefFromStart` (:1435–1442), `modelRefFromValue` (:1444–1447), `modelRefFromObject` (:1449–1456), `sleep` (:1375–1377); consumeEvents wiring per pass-26 turn-settlement capsule (:855–925).
**Signature:** `runCompaction({ client, sessionId, start, turn, emit }): Promise<void>`; `resolveCompactionModel({ client, sessionId, start }): Promise<{providerID: string; modelID: string} | undefined>`.
**Data Shape:** settle sources into ONE deferred (`compactionSettled`): explicit ended events (`session.next.compaction.ended` / `session.compacted`), busy→idle status transition (only after `sawBusy` — a retry status also sets sawBusy and emits a warning), or `session.error` (terminalError captured via formatError). Trigger = `legacySessionSummarize` calling `client.session.summarize({sessionID, auto:false, providerID, modelID})`. Fallback emission = `{type:'compaction', trigger:'manual', summary:'', harnessMetadata:{opencode:{missingSummary:true}}}`.

### Decisive source
```ts
// index.ts:828–852 (abridged) — trigger, race the settle against a 250ms grace, then reconcile
const compacted = await legacySessionSummarize({ client, sessionId, model });
if (compacted.error) { eventsAbort.abort(); throw new Error(`OpenCode compaction failed: ${formatError(compacted.error)}`); }
await Promise.race([compactionSettled.promise, sleep(250)]);
eventsAbort.abort();
await eventLoop.catch(() => {});
if (terminalError) throw new Error(terminalError);
if (!sawCompaction) {
  emit({ type: 'compaction', trigger: 'manual', summary: '', harnessMetadata: { opencode: { missingSummary: true } } });
}
```

**Flow:** runTurn branches on `start.operation === 'compact'` BEFORE any prompt work (no runPrompt, no usage accounting — the finally still closes user messages and emits a finish with defaultUsage). runCompaction first resolves the model through a three-rung ladder where every rung degrades on fetch failure (.catch(()=>undefined)): (1) latest assistant snapshot — its `model` field, else the snapshot object itself, else `metadata.assistant`, each requiring both providerID and modelID(??id); (2) session info from legacySessionGet — `session.model` then the session object itself; (3) the start frame — splitModel(start.model, start.provider) with provider fallback `OPENAI_NAME ?? 'anthropic'`. No rung yields a ref ⇒ hard throw ('requires a previous turn or an explicit model'). Then it opens a consumeEvents loop whose emit wrapper watches for the translated `compaction` event (sawCompaction) while onEvent feeds the settle deferred as described above; triggers the native summarize; on API error aborts the events and throws; otherwise races the settled promise against sleep(250) — a grace window so a fast compaction whose ended-event lands just after the API returns is still caught — then aborts the events, drains the loop swallowing its rejection, throws if a terminal error was observed, and emits the synthetic missingSummary compaction ONLY when no real one was seen.
**Invariant:** consumers see EXACTLY ONE compaction event per compact operation — either the runtime's real one (with summary/recent metadata) or the synthetic missingSummary marker, never both and never zero; the synthetic event is distinguishable by harnessMetadata.opencode.missingSummary so downstream can tell "compacted, summary unavailable" from "compacted with summary"; the busy→idle settle requires sawBusy first so an idle status that predates the operation cannot settle it early; model resolution prefers what the SESSION actually used (assistant snapshot) over what the host requested, so a mid-session model switch does not compact with the wrong model; every fetch failure in the ladder degrades to the next rung rather than failing the operation.
**Probe:** NO direct test drives runCompaction — index.test.ts (138L) pins only the step.failed settlement path of runPrompt; the EVENT side of the same seam IS test-pinned: create-emit-stream-event.test.ts :343–377 ('preserves retry, error, compaction, and file events') pins `session.next.compaction.ended` ⇒ `{type:'compaction', trigger:'auto', summary:'summary', harnessMetadata:{opencode:{recent:'recent'}}}`. The operation side (settle race, model ladder, synthetic emission) is deterministic-read-only — recorded as coverage caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "runCompaction resolveCompactionModel legacySessionSummarize missingSummary", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the one-deferred multi-source settle for any long operation whose API return precedes its observable completion: feed explicit-ended events, a state-transition (busy→idle gated on having-seen-busy), and terminal errors into one resolve-once deferred, race it against a short grace sleep after the trigger returns, then drain and reconcile; adopt the degrade-downward model-resolution ladder (what the session last used → what the session says → what the caller asked, each rung catch-swallowed) whenever an operation must run under the session's own configuration; adopt the synthetic-fallback-with-marker pattern (emit a well-formed event flagged in harnessMetadata rather than emitting nothing or throwing) when the consumer contract requires exactly-one; adapt the grace duration to your runtime's event latency; omit the whole plane where the runtime's summarize API is synchronous or already streams its own completion. Bridge-side twin of the pass-23 host-side /compact rail (harness-opencode-compaction-rail.md: host buffers out-of-turn compaction parts and flushes at the next wireTurn; this capsule is the sandbox side that PRODUCES the event that rail consumes). Caveat: deterministic-read-only (no test drives the operation); the event translation it depends on is fully test-pinned.
