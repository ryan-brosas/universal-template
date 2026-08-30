<!-- capsule-v2 -->
# Call classification + bounded observation queue — how does raw CDP traffic become semantic action beats without ever stalling the protocol?

**Source:** browser-harness-js MIT `main@6b189406`; Codebase Memory `browser-harness-js`. **Question:** Which wire methods map to which user-visible action, and how does a wedged screenshot avoid poisoning every later action?

## classify table (release-paired), serialized queue with 4.5s escape hatch, frame dedup via beforeFrame
**Path/Symbol:** `skills/cdp/sdk/recording.ts:classify` (:210-253), `RecordingManager.observe` (:302-312), `waitForQueue` (:361-369), `nextFrameNumber` (:395-408).
**Signature:** `classify(call: CdpCallObservation): SemanticAction | undefined` where `SemanticAction = { helper, delayMs, details }`; `observe = async (call) => void`.
**Data Shape:** classified helpers: `goto_url` (Page.navigate/reload/history-entry; scrubbed `to`) · `click_at_xy` (mouseReleased OR touchEnd — pressed is deliberately NOT a beat) · `scroll` (mouseWheel with dx/dy) · `type_text` (Input.insertText, text capped at 500 chars) · `press_key` (keyUp only, key → `<character>` when len 1) · `upload_file` (DOM.setFileInputFiles → count only).

### Decisive source
```ts
const operation = this.queue.then(() => this.observeAction(call, action), () => this.observeAction(call, action)).catch(() => {});
this.queue = operation;
if (!await this.waitForQueue(operation) && this.queue === operation) {
  // A wedged screenshot must not impose the timeout on every later action.
  // The old best-effort operation may still finish independently.
  this.queue = Promise.resolve();
}
```
with `waitForQueue(queue, timeoutMs = 4_500)` racing the tail against a timer (resolve-on-either-outcome).

**Flow:** observer fires on SUCCESSFUL calls only (installed via `session.setCallObserver`) → classify to a beat or `undefined` (noise) → enqueue capture behind the previous one → each capture waits its `delayMs` settle (so post-action frames show the result), evaluates page context, screenshots JPEG q80, numbers frames monotonically per directory (`frameNumbers` cache seeded from a directory scan at max+2 so restarts don't collide), links the previous frame as `beforeFrame` for click pairs → append JSONL.
**Invariant:** (1) PAIRED-EVENT DISCIPLINE: record on the release half of input pairs (mouseReleased/keyUp/touchEnd), never the press half, or every click double-counts. (2) The queue is serialized (screenshots are expensive and must not interleave) but NOT trusted: a wedged operation is ABANDONED by swapping `queue = Promise.resolve()` while the old op still runs detached — latency never compounds. (3) Recording must never change protocol behavior: observer failures and screenshot failures are swallowed after metadata is preserved. (4) Only calls WITH a sessionId (page-scoped) become beats.
**Probe:** direct tests `skills/cdp/sdk/video.test.ts` drive `observe({method:'Input.insertText'…})` through real files twice (masked + fail-closed scenarios). Classification table source-pinned: `grep -n "helper: '" skills/cdp/sdk/recording.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness-js", query: "classify", limit: 3, fields: ["signature", "name", "file"] });
// resolves recording.classify @ recording.ts:210-253
```

## Verdict
Adopt release-half classification + abandonable serial queue for any observer bolted onto a hot path; adapt delay budgets (500/250/180/90ms ladder) to your latency tolerance; omit the touch branch if you never drive touch devices.
