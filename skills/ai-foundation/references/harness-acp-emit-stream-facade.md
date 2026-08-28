<!-- capsule-v2 -->
# ACP emit-stream composition facade — how do you wire a stream translator and a host-tool correlator into one emit surface without either owning the other?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** Pass-22 documented the ACP stream translator and host-tool correlation as separate kernels — but a porter wiring them from scratch faces the composition question: which one sees the message first, who closes whom, and how do permission-side tool calls enter a translator that normally consumes agent-emitted updates?

## One facade, fixed routing, terminal short-circuit
**Path/Symbol:** `packages/harness-acp/src/v1/bridge/create-emit-stream-event.ts` — `createEmitStreamEvent` (:14–104, stop short-circuit :77–82, permissionToolCall reshaping :90–96); wiring `bridge/index.ts` :233–241 (construction once per bridge), consumption in the turn loop (:299–316 message routing, :288–291 raw drain + close on error).
**Signature:** `createEmitStreamEvent({ emit, emitToolCallCandidate, builtinTools, hostToolServerName, hostTools }): { message, raw, close, permissionToolCall, claimHostToolPermission, hostToolCall, hostToolResult, registerHostToolCorrelationInvocation, removeHostToolCorrelationInvocation }` — `message({ message, rawUpdate }): boolean` returns true iff the message was terminal.
**Data Shape:** the facade owns ONE translator (createACPStreamTranslator over emit + emitToolCallCandidate + builtinTools) and ONE correlation (createHostToolCorrelation whose emitSemanticUpdate feeds translator.update with `preserveRaw: false` and whose emitRawUpdate feeds translator.raw). The `rawUpdate` parameter is the stream-capture sidecar's raw twin (see harness-acp-stream-capture-sidecar.md) — semantic updates carry their raw payload through the facade, not around it.

### Decisive source
```ts
// create-emit-stream-event.ts:77–82 — terminal messages bypass correlation entirely
message: ({ message, rawUpdate }) => {
  if (message.kind === 'stop') {
    correlation.close();
    translator.finish(message.response);
    return true;
  }
  correlation.update({ message, rawUpdate });
  return false;
},
```

**Flow:** every non-terminal session message hits correlation FIRST (it may synthesize host-tool semantic updates — announce/result pairs for tools the bridge executes host-side — which flow into the translator as if the agent had emitted them, tagged preserveRaw:false); messages correlation does not consume pass to the translator via its own update path. Permission-side tool calls (the host answering a requestPermission prompt) enter through `permissionToolCall`, which reshapes the `ToolCallUpdate` into a `tool_call_update` session update so the translator sees one uniform shape. Host-tool call/result emission and correlation invocation registration pass through unchanged. `close()` closes correlation then translator; on stream error the bridge drains raw values, then closes via the same facade.
**Invariant:** exactly one translator and one correlation per bridge lifetime (constructed once, reused across turns); terminal 'stop' messages close correlation BEFORE finishing the translator (host-tool bookkeeping settles before the step closes) and never reach correlation.update; the boolean return is the only terminality signal — callers must stop consuming after true; permission-side and agent-side tool calls are indistinguishable downstream (both arrive as tool_call_update); the raw channel is separate from the semantic channel (raw values bypass correlation entirely).
**Probe:** NO dedicated unit test drives the facade — the two kernels it composes are fully test-pinned (stream-translator.test.ts 1303L, host-tool-correlation.test.ts 647L, both read whole in pass 22) and the bridge-level turn loop is exercised through acp-harness.test.ts; the facade's own routing (stop short-circuit, permission reshaping, preserveRaw:false tagging) is deterministic-read-only — recorded as coverage caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "createEmitStreamEvent permissionToolCall claimHostToolPermission correlation translator composition", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the facade pattern when composing a semantic translator with a synthesizing middle layer: route messages through the synthesizer first, give it a dedicated channel into the translator (with raw preservation explicitly disabled for synthesized events), short-circuit terminals before the synthesizer, and return terminality as a value so the consumer's loop stays flat. Adopt the reshape-at-the-door rule for out-of-band tool calls (permission answers become ordinary tool_call_update) so the translator never learns a second shape. Adapt the terminal kind to your protocol; omit the facade where the two kernels are always used separately. Coverage caveat: deterministic-read-only facade (composed kernels fully test-pinned); closes the pass-22 "translator/correlation assumed seam" gap named in the ledger.
