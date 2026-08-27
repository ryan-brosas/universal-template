<!-- capsule-v2 -->
# transform-messages-preshaper — How do I pre-shape a cross-model message history so ANY provider converter receives a legal wire sequence?

**Source:** pi-mono (MIT) `main@80e62761f7251a104f1b21d9c73920c720f0ec00`; Codebase Memory `pi-mono`. **Question:** Which repairs must run on a stored conversation before per-provider conversion, and how are thinking signatures, tool-call ids, and orphaned tool calls reconciled across model switches?

## Shared pre-converter consumed by every API
**Path/Symbol:** `packages/ai/src/api/transform-messages.ts` whole 223L — `transformMessages` :64-223, `insertSyntheticToolResults` :163-180, `downgradeUnsupportedImages` :35-57, `replaceImagesWithPlaceholder` :15-33. Trace: inbound callers_total=25 — buildParams/stream/streamSimple of anthropic-messages, azure-openai-responses, bedrock-converse-stream, google-generative-ai, google-vertex, mistral-conversations, openai-codex-responses (incl. processWebSocketStream), openai-completions, openai-responses + shared converters.
**Signature:** `export function transformMessages<TApi extends Api>(messages: Message[], model: Model<TApi>, normalizeToolCallId?: (id: string, model: Model<TApi>, source: AssistantMessage) => string): Message[]`.
**Data Shape:** in/out are `Message[]` (user/assistant/toolResult); the id remap is an internal `Map<originalId, normalizedId>` applied to later `toolResult.toolCallId`s; synthetic results are `toolResult` with `isError:true`, text `"No result provided"`.

### Decisive source
```ts
if (msg.role === "assistant") {
    // Skip errored/aborted assistant messages entirely.
    // These are incomplete turns that shouldn't be replayed:
    // - Replaying them can cause API errors (e.g., OpenAI "reasoning without following item")
    const assistantMsg = msg as AssistantMessage;
    if (assistantMsg.stopReason === "error" || assistantMsg.stopReason === "aborted") { continue; }
    ...
} else if (msg.role === "user") {
    insertSyntheticToolResults();   // user interrupt closes pending tool calls
    result.push(msg);
}
...
insertSyntheticToolResults();       // end-of-history closes them too
```

**Flow:** Pass 0 normalizes null content to `[]` and downgrades image blocks when `!model.input.includes("image")` — CONSECUTIVE images collapse into ONE placeholder so histories never accumulate duplicate "(image omitted)" texts. Pass 1 walks messages with the same-model gate `provider === model.provider && api === model.api && model.id === model.id`: thinking blocks — `redacted` kept ONLY same-model; signature-bearing kept even with EMPTY text when same-model (encrypted-reasoning replay); empty unsigned dropped; otherwise downgraded to a plain text block. Cross-model toolCalls lose `thoughtSignature` and get ids rewritten through the per-provider callback (anthropic: strip to `[a-zA-Z0-9_-]` ≤64; Responses: composite `call|item` grammar), with old→new recorded for paired toolResults. Pass 2 skips `stopReason: "error"|"aborted"` assistant messages entirely and inserts synthetic error toolResults for orphaned calls at three boundaries: next assistant message, user interrupt, end of history.
**Invariant:** Every toolCall that survives must have exactly one toolResult after the transform (synthesized if needed) — no provider converter may receive a dangling call; thinking signatures must never cross model boundaries (opaque encrypted content is same-model-only); id normalization must be bijective within one transform so paired results follow their calls.
**Probe:** `packages/ai/test/transform-messages-copilot-openai-to-anthropic.test.ts` — GREEN live 4/4 at pin: cross-model thinking→text conversion, thoughtSignature stripped on migration, synthetic result for trailing orphan (`"call_123|fc_123"` → `"call_123_fc_123"`), and selective synthesis when only ONE of two calls lacks a result. Related live suites: `test/tool-call-without-result.test.ts`, `test/image-tool-result.test.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-mono", query: "transform messages normalize tool call id synthetic tool result image downgrade thinking signature", limit: 10, fields: ["signature", "name", "file"] });
```
Live result at pin: test `anthropicNormalizeToolCallId` #1 (-42.18), `insertSyntheticToolResults` #2 (-40.26), `downgradeUnsupportedImages` #5, plus the per-provider `normalizeToolCallId` twins (anthropic-messages :1116-1118, openai-completions :1139-1163, google-shared :133-136).

## Verdict
Adopt the three-pass shape (normalize+image-downgrade → per-message same-model gating → orphan synthesis) and the same-model triple gate verbatim; it is what makes session files portable across providers without tripping encrypted-content or pairing validators. Adapt only the normalizeToolCallId callback to each target provider's id grammar. Omit nothing silently: dropping the errored-turn skip or the consecutive-image collapse regresses real sessions (partial turns and stacked screenshots are the common case, not the edge).
