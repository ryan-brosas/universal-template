<!-- capsule-v2 -->
# Delayed-enrichment pending-write drain — how do you await in-flight async enrichment writes before finalize/shutdown?

**Source:** OpenOats MIT `main@bc0ddb9d5d12`; Codebase Memory `openoats`. **Question:** An utterance append kicks off a delayed async task that enriches the record (suggestion snapshot, conversation summary, cleaned text) before persisting it — what is the protocol that lets a finalizer wait until every such write has landed?

## Counter + continuation-waiter drain
**Path/Symbol:** `OpenOats/Sources/OpenOats/Storage/SessionRepository.swift:appendRecordDelayed` (:362–407), `decrementPendingWrites` (:409–418), `awaitPendingWrites` (:421–426); entry routing `appendLiveUtterance` (:319–341) via `LiveUtteranceMetadata.isDelayed`.
**Signature:** `private func appendRecordDelayed(baseRecord: SessionRecord, utteranceID: UUID?, suggestionEngine: SuggestionEngine?, transcriptStore: TranscriptStore?)`; `func awaitPendingWrites() async`; state `private var pendingWrites = 0; private var pendingWriteWaiters: [CheckedContinuation<Void, Never>]`.
**Data Shape:** Delayed path: increment counter → detached Task sleeps 5s → re-snapshots engine log snapshot / short summary / cleanedText by utterance id → rebuilds an enriched SessionRecord (base text/timestamp preserved) → `appendRecord(enriched)` → decrement.

### Decisive source
```swift
pendingWrites += 1
Task { [weak self] in
    try? await Task.sleep(for: .seconds(5))
    guard let self else { return }
    /* ... snapshot enrichment ... */
    await self.appendRecord(enrichedRecord)
    await self.decrementPendingWrites()
}
// decrementPendingWrites:
if pendingWrites == 0 {
    let waiters = pendingWriteWaiters
    pendingWriteWaiters.removeAll()
    for waiter in waiters { waiter.resume() }
}
```

**Flow:** delayed append → counter+1 → 5 s enrichment window → enriched record appended → counter−1; at exactly zero, all parked continuations resume. `awaitPendingWrites` returns immediately when nothing is pending.
**Invariant:** Waiters resume only when the count reaches zero after having been positive — an awaiter can never observe "drained" while any enrichment write is un-landed, and resume happens once per waiter (the array is drained before resuming). A deallocated repository (`[weak self]`) abandons the write rather than crashing.

**Probe:** `OpenOats/Tests/OpenOatsTests/SessionRepositoryTests.swift:testAppendMultipleUtterances` (:151–171) exercises repeated appends through the same actor and asserts full ordered persistence.

## Get live surrounding code
**Retrieve:** (executed live at pin)
```ts
await mcp.codebase_memory.search_graph({ project: "openoats", query: "appendRecordDelayed pendingWrites awaitPendingWrites drain", limit: 10, fields: ["signature", "file"] });
// total 4: rank 2 = …SessionRepository.appendRecordDelayed :362-407,
// rank 3 = …SessionRepository.awaitPendingWrites :421-426
```

## Verdict
Adopt the counter-plus-continuation drain as the shutdown/finalize gate for backgrounded enrichment writes; the zero-crossing resume point is the load-bearing detail. Adapt the 5-second delay and Swift Task to your scheduler (setTimeout + promise gate works identically); keep enrichment read-after-snapshot semantics (snapshot taken inside the task, not at enqueue). Omit the weak-self abandonment if your host guarantees owner lifetime.
