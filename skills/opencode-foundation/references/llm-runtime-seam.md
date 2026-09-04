<!-- capsule-v2 -->
# LLM runtime seam — how does one stream call route between the native runtime, the AI SDK, and a workflow tool bridge?

**Source:** opencode (Slate-licensed monorepo) @ `dev@4643e65a`; Codebase Memory `opencode`. **Question:** How does opencode pick an LLM execution runtime per call, repair malformed tool calls, and bridge tool execution for server-side workflow models?

## Dual-runtime selection with logged fallback
**Path/Symbol:** `packages/opencode/src/session/llm.ts` (layer `run` :85–355; `stream` :357–381; `OUTPUT_TOKEN_MAX` re-export :33).
**Signature:** `stream(input: StreamInput) → Stream<LLMEvent>`; internal `run(input: StreamRequest) → {type:"native", stream} | {type:"ai-sdk", result}`.
**Data Shape:** `StreamInput = {user, sessionID, parentSessionID?, model, agent, permission?, system[], messages, small?, tools, retries?, toolChoice?}`; both runtimes normalize to the SAME `LLMEvent` union consumed by the processor.

### Decisive source
```ts
// llm.ts:226-258 — native is opt-in and may decline; the REASON is logged, never thrown
if (flags.experimentalNativeLlm) {
  const native = LLMNativeRuntime.stream({ model, provider: item, auth: info, llmClient,
    messages: prepared.messages, tools: prepared.tools, ... })
  if (native.type === "supported") {
    yield* Effect.logInfo("llm runtime selected", { "llm.runtime": "native", ... })
    return { type: "native" as const, stream: native.stream }
  }
  yield* Effect.logInfo("llm runtime selected", { "llm.runtime": "ai-sdk", ..., "llm.native_unsupported_reason": native.reason })
}
return { type: "ai-sdk" as const, result: streamText({ ... }) }   // :278 default path
```

**Flow:** Request prep runs first (`LLMRequestPrep.prepare` :106) resolving language model + auth + tools. When `experimentalNativeLlm` flag is on, the native adapter over `@opencode-ai/llm` either returns a ready event stream (`supported`) or a concrete fallback reason — selection is LOGGED with `"llm.runtime"` attribute either way (:244/:254/:271). The AI SDK path wraps the provider language model in a v3 middleware whose `transformParams` (streams only) rewrites the prompt through `ProviderTransform.message` (:325-343), sets `maxRetries: input.retries ?? 0` (retry policy lives in the processor's Schedule, not here), and gates `includeRawChunks` to github-copilot providers only because Copilot returns authoritative billed cost in provider-specific fields (:294-295 comment).
**Invariant:** The two runtimes must expose identical LLMEvent semantics — the processor cannot tell them apart. A porter adding a third runtime must return the same discriminated union `{type, stream|result}`, not invent a third branch shape.
**Probe:** `packages/opencode/test/session/llm.test.ts` — ":1347 streams OpenAI through native runtime when opted in", ":1514 executes OpenAI tool calls through native runtime".

## Broken-tool-call salvage ladder
**Path/Symbol:** same file, `experimental_repairToolCall` :296–312; `activeTools` :317.

### Decisive source
```ts
// llm.ts:296-312 — case-repair first, then reroute to a sink tool so the loop keeps moving
async experimental_repairToolCall(failed) {
  const lower = failed.toolCall.toolName.toLowerCase()
  if (lower !== failed.toolCall.toolName && prepared.tools[lower]) {
    return { ...failed.toolCall, toolName: lower }              // 1st resort: case fix
  }
  return {
    ...failed.toolCall,
    input: JSON.stringify({ tool: failed.toolCall.toolName, error: failed.error.message }),
    toolName: "invalid",                                        // 2nd resort: invalid-sink
  }
},
activeTools: Object.keys(prepared.tools).filter((x) => x !== "invalid"),   // never offered TO the model
```

**Flow:** When the AI SDK reports an unparseable/unknown tool call, opencode first tries lowercasing the name (models often emit `Bash` for `bash`); if that hits a real tool the call proceeds normally. Otherwise the call is rerouted to the built-in `invalid` tool with the original name + error JSON as input — the assistant still receives a tool RESULT (the error narrative) instead of the stream dying. `invalid` is excluded from `activeTools` so it can only be reached via repair, never selected by the model.
**Invariant:** The repair ladder exists to keep the LOOP alive: every failure becomes data the model reads. `invalid` must stay out of activeTools or models will learn to call it deliberately.
**Probe:** direct source pin:
```bash
grep -n 'repairToolCall\|"invalid"' packages/opencode/src/session/llm.ts packages/opencode/src/tool/registry.ts | head -8
```
expect llm.ts :296/:310/:317 plus registry.ts invalid-tool definition lines.

## GitLab workflow tool bridge
**Path/Symbol:** same file :105–206 (isWorkflow detection :105, executor injection :119–148, preapproval :149–153, approval handler :155–205).

### Decisive source
```ts
// llm.ts:127-147 — DWS workflow models execute tools through opencode's own registry
workflowModel.toolExecutor = async (toolName, argsJson, _requestID) => {
  const t = prepared.tools[toolName]
  if (!t || !t.execute) return { result: "", error: `Unknown tool: ${toolName}` }
  try {
    const result = await t.execute!(JSON.parse(argsJson), { toolCallId: _requestID, messages, abortSignal })
    const output = typeof result === "string" ? result : (result?.output ?? JSON.stringify(result))
    return { result: output, metadata: ..., title: ... }
  } catch (e) { return { result: "", error: e.message ?? String(e) } }
}
// llm.ts:150-153 — anything NOT ask-gated by the merged ruleset is preapproved server-side
const ruleset = Permission.merge(input.agent.permission ?? [], input.permission ?? [])
workflowModel.sessionPreapprovedTools = Object.keys(prepared.tools).filter((name) => {
  const match = ruleset.findLast((rule) => Wildcard.match(name, rule.permission))
  return !match || match.action !== "ask"
})
```

**Flow:** Workflow models run server-side, so tool calls arrive over a WebSocket instead of locally; `toolExecutor` adapts them onto opencode's tool registry and returns string outputs/errors (never throws — errors ride as `{result:"",error}`). Permissioning mirrors local behavior: agent+call rulesets merge, last matching rule wins (`findLast`), and only non-`ask` tools are preapproved. Interactive approvals go through `perm.ask` under `permission:"workflow_tool_approval"` with a session-lifetime `approvedToolsForSession` Set preventing infinite approval loops for repeated MCP tools (:158-161); the events subscription is unsubscribed in `finally`.
**Invariant:** Executor failures are VALUES not exceptions (server-side caller can't catch). Preapproval must use the MERGED ruleset — checking only the agent's rules would silently widen server-side permissions beyond what a per-call ruleset narrows.
**Probe:** direct source pin:
```bash
grep -n 'sessionPreapprovedTools\|workflow_tool_approval\|toolExecutor' packages/opencode/src/session/llm.ts
```
expect :123,:125,:150,:156,:190,:198,:198 region hits all inside the isWorkflow block.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "streamText wrapLanguageModel middleware transformParams", limit: 5 });
// resolves the ai-sdk arm of LLM.run (llm.ts:278-355); Effect-gen closures themselves are NOT graph nodes (known class)
```

## Verdict
Adopt the dual-runtime seam contract (same event union, logged fallback reason), the case-fix→invalid-sink repair ladder with hidden-from-activeTools invariant, and the value-not-throw workflow toolExecutor with merged-ruleset preapproval; adapt transport specifics; omit GitLab product wiring.
