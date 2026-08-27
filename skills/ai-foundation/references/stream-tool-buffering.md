<!-- capsule-v2 -->
# Buffered stream-time tool execution — why queue tool calls instead of executing them at chunk time?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** How does the streaming executor order approval resolution against execution, and why must execution wait for the model-call-end boundary?

## Stream-time execution buffer
**Path/Symbol:** `packages/ai/src/generate-text/execute-tools-from-stream.ts:executeToolsFromStream` (:35–251); buffer `toolCallsToExecute` declared :79; flush at `case 'model-call-end'` (:200–250).
**Signature:** `executeToolsFromStream({stream, tools, callId, messages, abortSignal, timeout, experimental_sandbox, toolsContext, toolApproval, runtimeContext, toolApprovalSecret, generateId, ...}) => ReadableStream<ExecuteToolsStreamPart>`.
**Data Shape:** Per-chunk switch forwards every chunk immediately (`controller.enqueue(chunk)` FIRST), then classifies `tool-call` chunks: invalid → skip; unknown tool name → skip (provider-executed dynamic tools); `not-applicable` approval status executes directly without consuming an id; user-approval enqueues only a request part; denied/auto-denied enqueue a synthetic request+response PART PAIR; everything executable accumulates in the buffer.

### Decisive source
```ts
case 'model-call-end': {
  if (!isToolExecutionAllowedFinishReason(chunk.finishReason)) {
    return;
  }
  await Promise.all(
    toolCallsToExecute.map(async toolCall => {
      // deliberately NOT awaited via recordSpan — process next chunks while
      // long tools run
      const result = await executeToolCall({ ... });
      if (result != null) {
        controller.enqueue({ type: 'tool-execution-end',
          toolCallId: result.output.toolCallId,
          toolExecutionMs: result.toolExecutionMs });
        controller.enqueue(result.output);
      }
    }),
  );
  return;
}
```

**Flow:** chunk arrives → forward verbatim → resolve approval policy (may mint approvalId + optional HMAC signature via `maybeSignApproval`) → push to buffer if executable → at model-call-end gate on finish reason → execute all buffered calls in parallel, emitting `tool-execution-end` + result parts; tool errors become `{type:'error'}` parts, never throws.
**Invariant:** Approval ids are generated ONLY when an approval decision is representable on the wire — `not-applicable` calls skip `generateId()` entirely so callers relying on deterministic id sequences stay stable. Execution happens once per model call, AFTER its terminal state is known.
**Probe:** deterministic probes: `grep -c toolCallsToExecute.push packages/ai/src/generate-text/execute-tools-from-stream.ts` → `2` (not-applicable + approved paths); `grep -c "case 'model-call-end'" …` → `1`. Direct test: `execute-tools-from-stream.test.ts` (added alongside #19066/#19084 fixes).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "executeToolsFromStream toolCallsToExecute", limit: 10, fields: ["signature", "name", "file"] });
// verified live @9d9a73f: rank#1 executeToolsFromStream :35-251
```

## Verdict
Adopt buffer-until-boundary + parallel drain; adopt the not-applicable-skips-id-generation rule; adapt the approval signature scheme to your secret management; omit provider-specific sandbox plumbing. The complementary capsule `tool-execution-safety-gate.md` owns the finish-reason check itself.
