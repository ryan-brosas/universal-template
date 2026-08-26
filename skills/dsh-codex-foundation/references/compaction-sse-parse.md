<!-- capsule-v2 -->
# V2 compaction SSE parse — consume a Responses event stream strictly and assemble retained-history-plus-compaction output

**Source:** dsh-codex Apache-2.0 main@e3e54e206f7c829503c7e6eed378643ba0416792; Codebase Memory dsh-codex. **Question:** how do you parse a provider SSE stream into exactly one opaque compaction item plus terminal id/usage while failing closed on every malformed shape?

## compactResponse / consumeEvent
**Path/Symbol:** src/responses.ts:249-315 compactResponse (consumeEvent 259-288).
**Signature:** compactResponse(response: Response, retained: readonly unknown[]): Promise<CompactResponse> where CompactResponse = { id?: string; output: readonly unknown[]; usage?: JsonRecord }.
**Data Shape:** Reads the body reader incrementally, buffers across chunk boundaries, splits events on /\r?\n\r?\n/, joins consecutive data: lines, skips empty payloads and [DONE], tracks {compaction, responseId, usage, completed}, and returns [...retained, compactionItem].

### Decisive source
~~~ts
if (event['type'] === 'response.output_item.done') {
  const item = event['item']
  if (isRecord(item) && item['type'] === 'compaction') {
    if (compaction !== undefined) throw new Error('OpenAI Codex compact response contained multiple compaction items')
    compaction = item
  }
  return
}
if (event['type'] === 'response.failed' || event['type'] === 'error') {
  throw new Error('OpenAI Codex compact stream failed: ' + JSON.stringify(event).slice(0, 1000))
}
// response.completed / response.done require a record terminal with valid id/usage types, else throw;
// after EOF: completed must be true AND compaction present, then:
return { ...responseId === undefined ? {} : { id: responseId }, output: [...retained, compaction], ...usage === undefined ? {} : { usage } }
~~~

**Flow:** stream read → buffer split into SSE events → per event: collect the single compaction item, throw bounded-detail errors on failure events, capture terminal id/usage only after type validation → after EOF flush any trailing partial event → require completed AND compaction before returning retained+compaction.
**Invariant:** at most one compaction item (duplicate throws); a missing terminal event fails even if an item arrived; id/usage type violations fail closed; error details are JSON-truncated to 1000 chars; the reader lock is always released; unknown event types are ignored, not fatal.
**Probe:** tests/codex-compaction.spec.ts:70-88 compactionEvents fixture consumed by the runtime (assertions at 302-321 pin endpoint, thread-id header, store:false/stream:true/include body, and the exact input array); executed via pnpm test -- tests/codex-compaction.spec.ts.

## Get live surrounding code
**Retrieve:**
~~~ts
await mcp.codebase_memory.search_graph({ project: 'dsh-codex', qn_pattern: 'dsh-codex\\.src\\.responses\\.compactResponse', limit: 10, fields: ['signature', 'name', 'file', 'lines'] });
~~~

## Verdict
Adopt the boundary-safe buffering splitter, single-item collection with duplicate rejection, terminal-required completion, and 1000-char bounded diagnostics for any SSE state machine. Adapt event-type vocabulary and the sentinel item type to the target API. Omit Codex-specific encrypted_content handling. Coverage no_recorded_issue + metadata_match for src/responses.ts and tests/codex-compaction.spec.ts; malformed-terminal branches are source-confirmed beyond the suite happy path.
