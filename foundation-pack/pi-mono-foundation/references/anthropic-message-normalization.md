<!-- capsule-v2 -->
# Anthropic message normalization — how do arbitrary agent messages become a wire-valid Anthropic `messages` array without empty-block or tool-orphan rejections?

**Source:** pi-mono MIT `main@80e62761f7251a104f1b21d9c73920c720f0ec00`; Codebase Memory `pi-mono`. **Question:** Which messages may be dropped, merged, or rewritten when converting an internal conversation into Anthropic `MessageParam[]`, and what invariants keep the API from rejecting the request?

## Message → MessageParam conversion plane
**Path/Symbol:** `packages/ai/src/api/anthropic-messages.ts:convertMessages` (:1155-1320), with `convertToolResult` (:1120-1153).
**Signature:** `convertMessages(transformedMessages: Message[], isOAuthToken: boolean, cacheControl?: CacheControlEphemeral, allowEmptySignature = false, deferredToolNames: ReadonlySet<string> = new Set(), normalizeToolName: (name) => string = identity): MessageParam[]`
**Data Shape:** in: internal roles `user | assistant | toolResult`; out: alternating-role `MessageParam[]`. Per-message filters drop whitespace-only text; assistant `thinking` blocks carry optional `thinkingSignature`; consecutive `toolResult` messages coalesce into ONE user message.

### Decisive source
```ts
} else if (msg.role === "toolResult") {
    // Collect all consecutive toolResult messages, needed for z.ai Anthropic endpoint.
    const toolResults: ContentBlockParam[] = [];
    const siblingContent: ContentBlockParam[] = [];
    let j = i;
    while (j < transformedMessages.length && transformedMessages[j].role === "toolResult") { ... }
    i = j - 1;
    // Displaced reference-bearing results must follow every tool_result block.
    params.push({ role: "user", content: [...toolResults, ...siblingContent] });
}
```

**Flow:** user string/blocks → surrogate-sanitized, empties filtered (whole message skipped if nothing survives) → assistant text/thinking/toolCall → blocks (empty thinking dropped; missing signature downgraded to plain text unless `allowEmptySignature`; redacted thinking passed as opaque `redacted_thinking`) → runs of consecutive `toolResult`s folded into one user message whose blocks are `tool_result` first, displaced sibling content after → finally `cache_control` stamped on the last block of the last user message.
**Invariant:** Anthropic never sees an empty message, a dangling signature, or ordinary content mixed inside a `tool_result` that also carries `tool_reference` blocks (`convertToolResult` returns `{toolResult, siblingContent}` precisely because "Anthropic rejects tool references mixed with ordinary tool-result content").
**Probe:** `packages/ai/test/deferred-tools.test.ts:196-229` ("preserves tool output as sibling content after emitting references") pins the exact block order `[tool_result(call_1)=references, tool_result(call_2)="second result", text, image]`. NOTE: this suite is blocked at module import in this checkout (`src/models.generated.ts` needs gitignored generated catalogs); assertions were confirmed by direct read of test + source, and the sibling suite `image-tool-result.test.ts` covers the non-reference path.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-mono", query: "convertMessages anthropic message conversion provider request", limit: 20 });
// executed live this pass: ranked pi-mono.packages.ai.src.api.anthropic-messages.convertMessages :1155-1320 (#2),
// convertToolResult via query "convertToolResult tool_result sibling content image displaced" (#1, -28.75)
```

## Verdict
Adopt the normalization invariants (empty-drop, coalesced toolResults, signature downgrade ladder, sibling-content displacement, trailing cache_control). Adapt role names and block types to your host vocabulary. Omit Claude Code OAuth name mapping (`toClaudeCodeName`) unless you serve that surface. Coverage: all cited paths `no_recorded_issue` at generation 2026-08-24T16:11:21Z.
