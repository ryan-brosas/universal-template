<!-- capsule-v2 -->
# Finish-reason tool-execution safety gate — when may buffered tool calls actually execute?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** Before dispatching side-effecting tools after a model call ends, which terminal states are safe, and where must the gate sit so a truncated or failed stream can never execute a tool?

## Tool-call execution gate
**Path/Symbol:** `packages/ai/src/generate-text/is-tool-execution-allowed-finish-reason.ts:isToolExecutionAllowedFinishReason` (:3–7); consumed at `execute-tools-from-stream.ts:201` and `generate-text.ts:1265`.
**Signature:** `(finishReason: FinishReason) => boolean` — returns true ONLY for `'stop'` and `'tool-calls'`.
**Data Shape:** Input is the unified finish reason already known at the terminal chunk; output is a pure boolean with no access to tools or messages.

### Decisive source
```ts
export function isToolExecutionAllowedFinishReason(
  finishReason: FinishReason,
): boolean {
  return finishReason === 'stop' || finishReason === 'tool-calls';
}
```

**Flow:** Streaming path buffers approved/non-applicable tool calls into `toolCallsToExecute` during the step WITHOUT executing (`toolCallsToExecute.push` at :123/:194); on `model-call-end` the transform checks the gate (:200–203) — if the reason is not stop/tool-calls it returns and the buffer is silently discarded; non-streaming path checks the same predicate before running executionTools (:1263–1268).
**Invariant:** A model termination of `length`, `error`, `content-filter`, or `other` must never trigger tool execution, even for calls that passed approval — execution requires an explicitly healthy terminal state. Regression test parametrizes exactly these four reasons.
**Probe:** `packages/ai/src/generate-text/generate-text.test.ts:485` — `it.each(['length', 'error', 'content-filter', 'other'])('should not execute tools when the finish reason is %s')`; deterministic probe: `grep -cF "finishReason === 'stop' || finishReason === 'tool-calls'" packages/ai/src/generate-text/is-tool-execution-allowed-finish-reason.ts` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "isToolExecutionAllowedFinishReason", limit: 10, fields: ["signature", "name", "file"] });
// verified live @9d9a73f: rank#1 Function packages/ai/src/generate-text/is-tool-execution-allowed-finish-reason.ts :3-7
```

## Verdict
Adopt the two-value allowlist as a shared helper imported by BOTH streaming and non-streaming executors (a local reimplementation invites divergence); adapt the FinishReason type to your spec version; omit nothing — the gate is the entire contract. Porters who execute tools eagerly per-chunk instead of buffering until model-call-end lose the ability to check the terminal state at all.
