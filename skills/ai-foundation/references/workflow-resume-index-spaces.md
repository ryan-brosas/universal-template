<!-- capsule-v2 -->
# Workflow resume index spaces — why does a UI cursor crash when applied to a raw model stream?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** The transport counts UI chunks but the durable stream stores raw model parts — where must the resume cursor be applied?

## Replay-raw, transform-filtered cursor
**Path/Symbol:** `packages/workflow/src/to-ui-message-chunk.ts:createModelCallToUIChunkTransform({uiStartIndex})` (:224–264); documented server pattern in `workflow-chat-transport.ts` route example (#19109).
**Signature:** `uiStartIndex?: number` (default 0); throws `RangeError('uiStartIndex must be a non-negative safe integer')`.
**Data Shape:** Raw `ModelCallStreamPart`s in; `UIMessageChunk`s out with a running `uiChunkIndex` counter.

### Decisive source
```ts
if (!Number.isSafeInteger(uiStartIndex) || uiStartIndex < 0) {
  throw new RangeError('uiStartIndex must be a non-negative safe integer');
}
...
if (uiChunkIndex++ >= uiStartIndex) { /* emit */ }
```
Server resume pattern:
```ts
run.getReadable({ startIndex: 0 })                    // RAW stream from zero
   .pipeThrough(createModelCallToUIChunkTransform({ uiStartIndex: startIndex }));
```

**Flow:** raw parts and UI chunks are NOT one-to-one (one model part can fan out to multiple UI chunks), so applying a UI-space cursor to `getReadable` skips wrong entries, duplicates lifecycle framing, or omits canonical tool-turn chunks. Correct resume: replay raw from index 0, count UI chunks inside the transform, and emit only those at-or-after the caller's non-negative cursor.
**Invariant:** Negative cursors are illegal on this path BY CONSTRUCTION — negative tail indexes require a durable stream that ALREADY stores `UIMessageChunk` objects; mixing spaces is the bug class this exists to kill. Transport-side validation mirrors it: non-negative safe integer or HTTP 400.
**Probe:** deterministic probes: `grep -cF "if (uiChunkIndex++ >= uiStartIndex) {" packages/workflow/src/to-ui-message-chunk.ts` → `1`; `grep -cF "throw new RangeError('uiStartIndex must be a non-negative safe integer');" …ts` → `1`. Direct tests: `to-ui-message-chunk.test.ts` + `workflow-chat-transport.test.ts` resume suites.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "uiStartIndex createModelCallToUIChunkTransform", limit: 10, fields: ["signature","name","file"] });
// verified live @9d9a73f: rank#1 createModelCallToUIChunkTransform :224-264
```

## Verdict
Adopt replay-from-zero with in-transform UI-space filtering; adapt chunk fan-out counting to your converter; document the negative-index limitation in your transport contract exactly as upstream docs now do.
