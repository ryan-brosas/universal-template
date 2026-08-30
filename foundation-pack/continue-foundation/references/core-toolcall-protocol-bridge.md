<!-- capsule-v2 -->
# Core tool-call protocol bridge — how does a `tools/call` message from the client become an executed tool, and which errors throw versus become data?

**Source:** continue Apache-2.0 `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** Where exactly does the transport protocol meet the tool executor, and what is the throw-vs-data contract at each handler?

## Thin registration → strict bridge → never-reject executor; unknown-tool asymmetry across three sibling handlers

**Path/Symbol:** `core/core.ts:1047–1049` (`on("tools/call")`), `:1150–1189` (`private async handleToolCall`), sibling handlers `tools/evaluatePolicy` (:1051–1080) and `tools/preprocessArgs` (:1082–1113).
**Signature:** `handleToolCall(toolCall: ToolCall): Promise<{contextItems: ContextItem[]; errorMessage?: string; errorReason?: ContinueErrorReason}>`.
**Data Shape:** request carries a full `ToolCall`; response is the callTool result envelope (failure-as-data), while precondition failures THROW into the transport layer.

### Decisive source
```ts
on("tools/call", async ({ data: { toolCall } }) => this.handleToolCall(toolCall));

private async handleToolCall(toolCall: ToolCall) {
  const { config } = await this.configHandler.loadConfig();
  if (!config) throw new Error("Config not loaded");
  const tool = config.tools.find((t) => t.function.name === toolCall.function.name);
  if (!tool) throw new Error(`Tool ${toolCall.function.name} not found`);
  if (!config.selectedModelByRole.chat) throw new Error("No chat model selected");
  const onPartialOutput = (params) => this.messenger.send("toolCallPartialOutput", params);
  return await callTool(tool, toolCall, {
    config, ide: this.ide, llm: config.selectedModelByRole.chat,
    fetch: (url, init) => fetchwithRequestOptions(url, init, config.requestOptions),
    tool, toolCallId: toolCall.id, onPartialOutput, codeBaseIndexer: this.codeBaseIndexer,
  });
}
```

**Flow:** the bridge resolves the compiled config FRESH on every call (no cached tool list), requires a chat model for extras.llm, wraps fetch with the config's requestOptions so tool HTTP calls inherit org headers/proxy settings, and hands streaming output to the GUI via the `toolCallPartialOutput` messenger event — the ONLY path partial tool output reaches the UI. Everything inside `callTool` that can fail does so as data (funnel capsule); everything the BRIDGE needs to even dispatch throws. The sibling pair has a deliberate asymmetry: `tools/evaluatePolicy` returns `{policy: basePolicy}` UNCHANGED for an unknown tool name (:1060–1062, no fail-closed surprise) while `tools/preprocessArgs` THROWS ``Tool <name> not found`` for the same condition (:1089–1091) — policy evaluation must always answer something evaluable; preprocessing without a definition is a hard protocol error. preprocessArgs failures convert to `{preprocessedArgs: undefined, errorReason, errorMessage}`, preserving `ContinueError.reason`.
**Invariant:** dispatch-time unknowns throw; execution-time failures are data; policy-time unknowns are transparent. A porter porting this triangle must keep all three postures or clients will either crash on benign races (config reloaded mid-call) or silently auto-approve what they cannot evaluate.
**Probe:** no dedicated vitest suite exists for core.ts handlers (coverage caveat recorded this pass; core/core.ts itself is graph-clean `no_recorded_issue`). Deterministic check: the three postures are pinned by reading :1060 vs :1090 vs :1160 side by side. Port with a handler-level test table: {unknown tool × 3 handlers} → {basePolicy, throw, throw}, plus one "callTool throws ⇒ result.errorMessage" case.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "handleToolCall tools call protocol handler dispatch config tools", limit: 8 });
```

## Verdict
Adopt fresh-config-per-call resolution and the three-posture error taxonomy; adapt the extras bag (llm/fetch/codeBaseIndexer) to your runtime; omit the messenger streaming hop if your tools are request/response only. Trap: wrapping fetch with config requestOptions is load-bearing for enterprise deployments (custom CA/proxy headers) — dropping it breaks remote model/tool endpoints only inside tools, which is the hardest class of bug to notice.
