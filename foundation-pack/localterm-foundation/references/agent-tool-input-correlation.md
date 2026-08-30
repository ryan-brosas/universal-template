<!-- capsule-v2 -->
# Tool-call input correlation — how does a per-run log show WHAT each tool was invoked with when results carry no input?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853`; Codebase Memory `localterm`. **Question:** `tool_execution_end` events have no arguments — how do you attach the path/command to the right log entry across async execution?

## Bounded id→input map bridging message_end to tool_execution_end
**Path/Symbol:** `packages/server/src/agent-runner.ts:toolInputById` (:195, :238–261, :267–278).
**Signature:** `Map<string, string>` keyed by toolCallId; value = `truncateToolInput(formatToolInput(args))`.
**Data Shape:** Populated from `message_end` assistant content blocks (`type "tool_use"` OR `"toolCall"`, reading `arguments ?? block.input`) BEFORE the tool runs; consumed + deleted at `tool_execution_end`. Bounded at `AUTOMATION_SESSION_MAX_PENDING_TOOL_CALLS = 1_000` by evicting the OLDEST insertion-order key.

### Decisive source
```ts
while (toolInputById.size > AUTOMATION_SESSION_MAX_PENDING_TOOL_CALLS) {
                  const oldestToolCallId = toolInputById.keys().next().value;
                  if (oldestToolCallId === undefined) break;
                  toolInputById.delete(oldestToolCallId);
                }
```
```ts
} else if (event.type === "tool_execution_end") {
      ...
      const input = toolInputById.get(toolCallId);
      toolInputById.delete(toolCallId);
```

**Flow:** message_end carries tool_use {id, name, arguments} → formatted+truncated into the map → tool executes → tool_execution_end arrives with only toolCallId+result → map lookup attaches `input` to the log entry and DELETES the pending call. Same map/bounds reused by `agent-session-reader.ts` (`pendingToolCalls`, :61–70) for transcript flattening.
**Invariant:** Insertion-order eviction (Map preserves insertion order in JS) bounds memory on unbounded tool-call streams WITHOUT letting the map grow unbounded mid-run; delete-on-consume prevents stale inputs bleeding onto later same-id calls. `formatToolInput` renders command-first, then pattern·path, then path, then JSON fallback — mirroring pi's own per-tool display.
**Probe:** `packages/server/tests/agent-runner.test.ts` (`records a tool call's input (the path/command) on its log entry` :141–155 — FAKE_PI_TOOL_INPUT pins `{type:"tool", name:"read", input:"README.md", text:"# README"}` exactly).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "message_end tool_use toolCall truncateToolInput", limit: 10 });
```

## Verdict
Adopt the bounded insert-ordered correlation map + delete-on-consume; adapt formatToolInput's field ladder to your tool schemas. Directly tested end-to-end through the fake RPC stream.
