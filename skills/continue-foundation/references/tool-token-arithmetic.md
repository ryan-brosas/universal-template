<!-- capsule-v2 -->
# Tool-token arithmetic — how are function/tool definitions counted into the context budget without a tokenizer round-trip per field?

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** What is the exact constant-plus-encoding arithmetic for tools and chat messages, and which constants must survive a port verbatim?

## OpenAI-cookbook-derived overhead accounting
**Path/Symbol:** `core/llm/countTokens.ts:countToolsTokens` (:135-177), `countChatMessageTokens` (:179-218).
**Signature:** `countToolsTokens(tools: Tool[], modelName: string): number`; `countChatMessageTokens(modelName: string, chatMessage: ChatMessage): number`.
**Data Shape:** in → tool array (JSON-schema `parameters.properties` shape) / ChatMessage with optional `toolCalls`, `thinking`, `toolCallId`; out → integer token estimate.

### Decisive source
```ts
// https://community.openai.com/t/how-to-calculate-the-tokens-when-using-function-call/266573/10
let numTokens = 12;
for (const tool of tools) {
  let functionTokens = count(tool.function.name);
  if (tool.function.description) functionTokens += count(tool.function.description);
  for (const key in props) {
    functionTokens += count(key);
    if (fieldType)  { functionTokens += 2; functionTokens += count(fieldType); }
    if (fieldDesc)  { functionTokens += 2; functionTokens += count(fieldDesc); }
    if (fieldEnum && Array.isArray(fieldEnum)) {
      functionTokens -= 3;                       // enum replaces the default type cost
      for (const e of fieldEnum)
        functionTokens += 3 + (typeof e === "string" ? count(e) : 5);
    }
  }
  numTokens += functionTokens;
}
return numTokens + 12;   // trailing wrapper
```
```ts
const BASE_TOKENS = 4;                  // <|im_start|>{role}\n{content}<|end|>\n framing
const TOOL_CALL_EXTRA_TOKENS = 10;
const TOOL_OUTPUT_EXTRA_TOKENS = 10;    // "safety"
tokens += countTokens(JSON.stringify(call), modelName);   // whole tool call as JSON — TODO hone this, says source
if (chatMessage.role === "thinking") { /* redactedThinking + signature also counted */ }
```

**Flow:** per tool: 12 base + name + description + per-property (key text, +2/+type string, +2/description string, −3+3-per-entry enum). Per message: 4 framing + content + 10/tool-call (+ JSON-stringified call) + thinking extras + 10/tool-output (+ toolCallId).
**Invariant:** The enum branch SUBTRACTS 3 before adding 3-per-entry because an enum list REPLACES the plain type token cost — porters who only add double-count enums. Non-string enum entries cost flat **5**. These constants are the community-standard OpenAI approximation; they are deliberately conservative and vendor-agnostic (fed to any model).
**Probe:** deterministic source pins: `grep -n 'numTokens += 12\|numTokens + 12' countTokens.ts` → both wrappers; test suite `core/llm/countTokens.test.ts` exercises `countTokens`/prune paths; no dedicated direct unit for `countToolsTokens` at this pin (recorded caveat — behavior pinned by cited source ranges and the upstream cookbook reference).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "countToolsTokens countChatMessageTokens", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the constant table (12/12 tool wrappers, 4 message frame, 10 tool-call/output extras, ±3 enum swap, 5 non-string entries) and counting `JSON.stringify(call)` wholesale; adapt if your provider documents exact tool framing; omit nothing here without re-budgeting every caller. Coverage caveat: no dedicated direct test for this function — pinned by decisive source ranges.
