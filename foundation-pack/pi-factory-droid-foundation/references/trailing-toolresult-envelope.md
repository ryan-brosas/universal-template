<!-- capsule-v2 -->
# Trailing-toolResult envelope — how do I harvest just the newest tool results from a message history?

**Source:** pi-factory-droid MIT `master@e0a53248ab173b6f0ff763441c1f1160bedd016e`; Codebase Memory `pi-factory-droid`. **Question:** When the host history may contain many old tool-result rows, how do I extract only the batch produced since the last assistant turn and shape it for a foreign transport?

## Walk backward from the end; stop at the first assistant row
**Path/Symbol:** `src/tool-results.ts:extractAllToolResults` (30-57), `toolResultToMcpContent` (15-28); consumed by `src/pi-tools-mode.ts:deliverPiToolResults` (83-88).
**Signature:** `extractAllToolResults(messages: Array<{role, content?, toolCallId?, isError?}>): { results: BridgedToolResult[]; stopIdx: number }` — `toolResultToMcpContent(content: string | Block[]): McpContent`.
**Data Shape:** `BridgedToolResult = { content: [{type:"text",text}|{type:"image",data,mimeType}], isError?: boolean, toolCallId }`; Pi histories use roles `"user" | "assistant" | "toolResult"`.

### Decisive source
```ts
for (let i = messages.length - 1; i >= 0; i--) {
  const msg = messages[i];
  if (msg.role === "toolResult") {
    results.unshift({
      content: toolResultToMcpContent(msg.content),
      isError: msg.isError,
      toolCallId: msg.toolCallId,
    });
  } else if (msg.role === "assistant") {
    stopIdx = i;
    break;
  }
}
```

Content normalization never emits an empty array:
```ts
if (typeof content === "string") return [{ type: "text", text: content || "" }];
if (!Array.isArray(content)) return [{ type: "text", text: "" }];
// keep only well-formed text/image blocks...
return blocks.length ? blocks : [{ type: "text", text: "" }];
```

**Flow:** host's next streamSimple call → `deliverPiToolResults(board, context)` casts `context.messages` → backward scan collects every trailing `toolResult` until the assistant boundary (`stopIdx`) → `unshift` restores chronological order → `board.deliverResults(results)` resolves each hanging MCP handler by `toolCallId` (unknown/already-resolved ids are ignored or stashed as early results).
**Invariant:** Only the trailing result batch is delivered — older batches in the same history are never re-delivered (idempotent under repeated calls because resolved ids leave `pendingHandlers`). Output order matches history order. Malformed content degrades to one empty text block instead of an empty array.
**Probe:** `test/pi-tools-bridge.test.ts:74-86` ("collects trailing toolResult rows"): user+assistant prefix ignored, two trailing results collected in order, `isError: true` preserved on the second.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-factory-droid", query: "extractAllToolResults toolResultToMcpContent deliverPiToolResults BridgedToolResult", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt reverse-scan-to-assistant-boundary as the canonical "newest tool results only" extraction — it is O(batch), order-preserving, and idempotent. Adapt role names and the block union to your message schema. Omit the MCP content-type literals if your transport has its own envelope.
