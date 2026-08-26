<!-- capsule-v2 -->
# Sampling (createMessage) — how does a server request an LLM generation through the client, including tool use?

**Source:** modelcontextprotocol/specification MIT `main@4df2d6b`; Codebase Memory `modelcontextprotocol`. **Question:** What is the exact `sampling/createMessage` request/result contract, its tool-use loop, and its message-content constraints — and why is it deprecated?

## Server-driven LLM sampling via the client
**Path/Symbol:** `docs/specification/draft/client/sampling.mdx` (whole; capabilities :54–109; createMessage :111–162; sampling with tools :164–276; multi-turn tool loop :278–374; content constraints :376–458; cross-API compat :460–488; flow :490–678); wire types `schema/draft/schema.ts` (`CreateMessageRequestParams` :2104–2152, `ToolChoice` :2163–2171, `CreateMessageRequest` :2185–2188, `CreateMessageResult` :2210–2228, `SamplingMessage` :2245–2249).

**Deprecation:** Sampling is **deprecated** as of protocol `2026-07-28` (SEP-2577); remains in the spec ≥12 months; new implementations SHOULD NOT adopt it — migrate to integrating directly with LLM provider APIs. `includeContext: "thisServer"/"allServers"` values are deprecated (SEP-2596); omit the field or use `"none"`.

**Capabilities:** clients supporting sampling MUST declare `sampling` in `_meta.io.modelcontextprotocol/clientCapabilities` on each request. Basic: `{ "sampling": {} }`. Tool use: `{ "sampling": { "tools": {} } }` (servers MUST NOT send tool-enabled requests to clients that haven't declared `sampling.tools`). Context inclusion (deprecated): `{ "sampling": { "context": {} } }`.

### Decisive source
```jsonc
// sampling.mdx:115-162 (request + result shape)
// Server -> Client, inside InputRequiredResult.inputRequests:
{ "method": "sampling/createMessage", "params": {
    "messages": [{ "role": "user", "content": { "type": "text", "text": "..." } }],
    "modelPreferences": { "hints": [{ "name": "claude-3-sonnet" }],
      "costPriority": 0.3, "intelligencePriority": 0.8, "speedPriority": 0.5 },
    "temperature": 0.1, "systemPrompt": "You are a helpful assistant.",
    "includeContext": "thisServer", "maxTokens": 100 } }
// Client -> Server, inside inputResponses on the retried request:
{ "role": "assistant", "content": { "type": "text", "text": "The capital of France is Paris." },
  "model": "claude-3-sonnet-20240307", "stopReason": "endTurn" }
```

**CreateMessageRequestParams fields:** `messages` (required), `modelPreferences?` (client MAY ignore), `systemPrompt?` (client MAY modify/omit), `includeContext?` (`"none"|"thisServer"|"allServers"`, default `"none"`), `temperature?`, `maxTokens` (required), `stopSequences?`, `metadata?` (provider-specific), `tools?`, `toolChoice?`. **`tools`/`toolChoice` MUST NOT be sent unless the client declared `sampling.tools`** — the client MUST return an error if they're provided without that capability.

**Tool use in sampling:** servers can pass a `tools` array (scoped to the sampling request — need not correspond to registered tools) + optional `toolChoice` (`{mode:"auto"}` default / `"required"` / `"none"`). The LLM may return multiple `tool_use` content blocks (parallel tool use) with `stopReason: "toolUse"`. The server then executes the tools and sends a follow-up `sampling/createMessage` with history + `tool_result` blocks appended, repeating until the LLM returns a final text response (`stopReason: "endTurn"`). Servers may cap iterations and pass `toolChoice: {mode:"none"}` on the last iteration to force a final result.

**Message content constraints (critical):**
1. A user message containing tool results (`type: "tool_result"`) MUST contain **ONLY** tool results — mixing with text/image/audio is invalid (provider APIs use dedicated tool roles).
2. Every assistant message containing `ToolUseContent` blocks MUST be followed by a user message consisting entirely of `ToolResultContent` blocks, with each tool use (`id: $id`) matched by a corresponding tool result (`toolUseId: $id`) before any other message. This ensures tool uses resolve before the conversation continues and lets providers fetch results in parallel.

**Cross-API compatibility:** two roles (`user`/`assistant`); tool-use requests ride the `assistant` role, tool results ride `user`; `stopReason` is an open string (`endTurn|stopSequence|maxTokens|toolUse|provider-specific`).

**Invariant:** the tool-result-only user-message rule and the matched tool-use/tool-result pairing are the hard constraints a porter gets wrong — sending mixed content or an unmatched tool result breaks provider compatibility.

**Probe:** no runtime tests in the spec repo; wire types + `scripts/validate-examples.ts` are the machine-checkable anchors. Coverage caveat recorded honestly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "modelcontextprotocol", name_pattern: "CreateMessageRequest|SamplingMessage|ToolChoice|Sampling-With-Tools", limit: 10 });
```

## Verdict
Adopt the `sampling/createMessage` request/result contract, the capability-gated `sampling.tools` tool-use loop, and the tool-result-only + matched-pair message constraints if you must interoperate with legacy sampling; adapt model preferences, tool catalogs, and stop-reason mapping to host; **omit** for new implementations (deprecated SEP-2577 — integrate directly with LLM provider APIs instead).
