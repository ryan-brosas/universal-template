<!-- capsule-v2 -->
# toResponseMessages — how do a step's content parts become exactly one assistant message plus one tool message that every provider will accept back?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory project `ai`. **Question:** When porting history round-tripping, which parts are dropped vs routed, and in what order must tool results appear inside the tool message?

## toResponseMessages + sortToolResultContentByToolCallOrder
**Path/Symbol:** `packages/ai/src/generate-text/to-response-messages.ts:toResponseMessages` (:15–220), `sortToolResultContentByToolCallOrder` (:222–257).
**Signature:** `async function toResponseMessages<TOOLS>({ content: Array<ContentPart>, tools }): Promise<Array<AssistantModelMessage | ToolModelMessage>>`.
**Data Shape:** Input content is the merged provider+client part list from `asContent`. Output ≤2 messages: an assistant message (text/reasoning/file/tool-call/approval-request) and a tool message (tool-result / tool-error-as-result / approval-response / synthesized execution-denied result). A `toolCallOrder: Map<toolCallId, insertionIndex>` records first-appearance order of each tool call.

### Decisive source
```ts
// Assistant pass skips (in order):
if (part.type === 'source') continue;                    // response-only
if ((part.type === 'tool-result' || part.type === 'tool-error') &&
    !part.providerExecuted) continue;                    // -> tool message
if (part.type === 'text' && part.text.length === 0) continue;
// invalid tool-call input coercion:
input: part.invalid && typeof part.input !== 'object' ? {} : part.input,
// Tool message pass — denied approvals synthesize a result so the
// tool call never dangles (:169-182):
if (part.approved === false) {
  toolResultContent.push({
    type: 'tool-result', toolCallId: part.toolCall.toolCallId,
    toolName: part.toolCall.toolName,
    output: { type: 'execution-denied' as const, reason: part.reason },
  });
}
// Sort preserves relative order of unmatched ids; matched ids win (:236-248)
if (aOrder == null && bOrder == null) return a.index - b.index;
if (aOrder == null) return 1;
if (bOrder == null) return -1;
return aOrder - bOrder || a.index - b.index;
```
Error-mode asymmetry: provider-executed `tool-error` stays in the ASSISTANT message via `createToolModelOutput(errorMode:'json')` (:114–130); client-side errors go to the TOOL message with `errorMode:'text'` (:190–196).

**Flow:** Pass 1 builds assistant content (skip rules above; tool-call inputs sanitized) → push if non-empty. Pass 2 collects tool-message content: approval-responses verbatim (+synthesized execution-denied per denial), then non-provider-executed results/errors via `createToolModelOutput`. Sort tool-results by first tool-call appearance (stable for results with no matching call). Push tool message if non-empty.
**Invariant:** Every emitted tool-call gets a matching tool-result in the same turn's messages — denials synthesize `{type:'execution-denied'}` rather than leaving a hole. Parallel tool results must be reordered into tool-call issuance order even when execution finished out of order. Empty text/assistant content produce no message.
**Probe:** `packages/ai/src/generate-text/to-response-messages.test.ts` — parallel reorder "should serialize parallel tool results in tool call order" (:293), execution-denied synthesis (:1186), invalid-input sanitization (:1412/:1474), provider-executed routing (:816/:1354).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "toResponseMessages sortToolResultContentByToolCallOrder", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the two-pass split (assistant vs tool message), the three skip rules, execution-denied synthesis, and tool-call-order sorting of results. Adapt message/content type names and the error-mode choice to host providers; omit the approval-request stage if your host has no human-in-the-loop. Coverage caveat: best-effort index; excerpts read directly at HEAD.
