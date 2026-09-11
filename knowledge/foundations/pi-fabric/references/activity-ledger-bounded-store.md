<!-- capsule-v2 -->
# Activity ledger store — how do you keep a live run/call/item/event dashboard bounded, isolated, and stale-proof when streaming providers outlive their run?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** what is the full write-side contract of an in-memory activity ledger that a UI polls at up to 10 Hz — mutation gates, payload bounds, pruning, and read isolation?

## Bounded in-memory ledger with best-effort call tracking and lean summary reads
**Path/Symbol:** `src/activity/store.ts:FabricActivityStore` (:129-555); bounds :18-27; sanitizers `cleanText`/`cleanId`/`boundedData` (:35-65); lifecycle `start`/`resume`/`configure` (:151-193); phases `phase` (:195-250); items `upsertItem` (:252-312); events `event` (:314-329); calls `beginCall`/`updateCallArgs`/`updateCall`/`finishCall` (:333-464); settle `finish` (:466-496); reads `runs`/`runSummaries`/`get` (:498-513); prune/emit (:534-554); `leanRun` (:559-576). Direct tests `tests/activity-store.test.ts` (all 295 lines).
**Signature:** `start(id, display?) => FabricActivityRun`, `phase(runId, {name, id?, total?})`, `upsertItem(runId, {id?, label, status?, phase?, data?})`, `beginCall(runId, {callId, ref, args})`, `updateCall(runId, callId, {type:"progress"|"entity"|"metrics", …})`, `finishCall(runId, callId, {success, result?, preview?, error?})`, `finish(runId, success, error?)`, `runs()` / `runSummaries()` (ordered, isolated copies), all mutations return `structuredClone`s.
**Data Shape:** bounds `MAX_RUNS=24`, `MAX_CALLS=1_000`, `MAX_ITEMS=1_000`, `MAX_EVENTS=200`, name 120 / description 500 / detail 1_000 / data 8_000 chars, call payload 64_000 chars, call summary 120 chars; oversized payloads become `{fabricTruncated: true, originalChars, preview}`; ids sanitized to `[a-zA-Z0-9._:-]` with `-` fallback; metrics `{tokens?, toolCalls?, cost?}`.

### Decisive source
```ts
// beginCall is BEST-EFFORT by design (comment :331-332): streaming providers may
// report lifecycle events after session teardown reset()s the store.
beginCall(runId, input) {
  const run = this.#runs.get(runId);
  if (!run) return;                       // unknown/reset run ⇒ SILENT no-op
  const existing = index.get(input.callId);
  if (existing) { /* re-begin resets to running; deletes result/error/detail */ }
  if (run.calls.length >= MAX_CALLS) {
    const removed = run.calls.splice(0, run.calls.length - MAX_CALLS + 1);
    for (const call of removed) index.delete(call.id);   // index NEVER outlives list
  }
}
finishCall(...) {
  const resultFailed = isFailedResult(input.result);     // status failed/stopped/timed_out
  call.status = input.success && !resultFailed ? "completed" : "failed";
}
finish(runId, success, error?) {
  if (!run || run.status !== "running") return;          // double-finish no-op
  const cancelled = Boolean(error && /cancel(?:led|ed)/i.test(error));
  run.status = success ? "completed" : cancelled ? "cancelled" : "failed";
  // every still-running phase/call/item inherits the run's terminal status
}
runSummaries() // leanRun strips args/result/preview/data payloads; metrics shallow-copied
```

**Flow:** `#require(id)` throws `Unknown Fabric activity run: <id>` for DIRECTED workflow writes (`resume/configure/phase/upsertItem/event`) while call tracking uses silent get-or-bail — directed API is strict, streaming API is forgiving. `phase()` auto-completes the previous running phase when switching (:205-212), suffixes colliding ids `-2`, `-3…` (:217), and renames a default-named first-phase run ("Fabric program") to the phase name (:247). Item phase ownership is stable across updates unless `input.phase` explicitly moves it (:260-263, test :84-109 pins this exactly). `finishCall` derives entity id/kind and merges usage-metrics from the result object (:446-456) and only sets `detail` on completed calls via `summarizeCallResult` (output/content/text → whitespace-collapsed ≤120 chars; failed calls never get detail). `#emit()` bumps one revision counter and fans out to listeners inside per-listener try/catch (:547-554). Reads sort running-first then updatedAt desc (:526-532).
**Invariant:** every returned object is a `structuredClone` — callers can never mutate store state through reads or mutation returns (test :278-283 mutates a summary and asserts no leak); `#prune()` evicts ONLY non-running runs oldest-first so a live run is never dropped despite MAX_RUNS (:534-545); call-index deletion always mirrors list splices; `leanRun` keeps every remaining field scalar except shallow-copied metrics.
**Probe:** `bash -c 'cd $REFERENCE_ROOT/pi-ecosystem/pi-fabric && grep -n "if (!run) return;" src/activity/store.ts | wc -l'` → 4 (one per streaming call-API method); `grep -c "structuredClone(run" src/activity/store.ts` → 4; tests pin bounds end-to-end: `expect(call?.args).toMatchObject({ fabricTruncated: true })` :157, `expect(store.runs()).toHaveLength(24)` :167, `expect(JSON.stringify(call).length).toBeLessThan(200_000)` :160, resume clears finish: `expect(resumed).not.toHaveProperty("finishedAt")` :203, label derivation `"extensions.vcc_recall · how do I recall X"` :230, detail summarization `expect(bash?.detail).toBe("line1 line2")` :130, cancelled classification :214-218.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "FabricActivityStore runSummaries activity run phases calls items events", limit: 10, fields: ["signature", "name", "file"] });
```
(Rank #1 resolves `FabricActivityStore.runSummaries` line-exact at the pin.)

## Verdict
Adopt the two-tier API discipline (throwing directed writes vs silent streaming writes), clone-on-read isolation, running-first pruning, and the fabricTruncated envelope for any polled in-memory activity/dashboard store; adapt the numeric bounds to your UI cadence; omit the metrics-merge ladder if your results carry no usage. All branches are direct-test-pinned — no coverage caveat.
