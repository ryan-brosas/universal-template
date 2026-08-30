<!-- capsule-v2 -->
# Tool-call ID sanitation — how do you make arbitrary provider IDs legal for every API?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** Providers emit tool_use ids with dots, colons, URLs and >64-char lengths — what is the sanitize/truncate contract that keeps history replay valid on strict APIs (OpenAI Responses API)?

## Character whitelist first, then length cap with MD5 disambiguation suffix
**Path/Symbol:** `src/utils/tool-id.ts` (`OPENAI_CALL_ID_MAX_LENGTH = 64` :7, `sanitizeToolUseId` :13-15, `truncateOpenAiCallId` :25-42, `sanitizeOpenAiCallId` :52-55).
**Signature:** `sanitizeToolUseId(id: string): string`; `truncateOpenAiCallId(id: string, maxLength = 64): string`; `sanitizeOpenAiCallId(id: string, maxLength? = 64): string`.
**Data Shape:** Valid charset `^[a-zA-Z0-9_-]+$` (API validation pattern); truncation reserves `_` + 8 hex chars: prefix keeps 55 chars.

### Decisive source
```ts
export function sanitizeToolUseId(id: string): string {
    return id.replace(/[^a-zA-Z0-9_-]/g, "_")   // dots/colons/slashes → underscore
}
export function truncateOpenAiCallId(id: string, maxLength = OPENAI_CALL_ID_MAX_LENGTH): string {
    if (id.length <= maxLength) return id
    const hashSuffixLength = 8                  // md5(id) prefix — collision-resistant ENOUGH here
    const separator = "_"
    const prefixMaxLength = maxLength - separator.length - hashSuffixLength
    const hash = crypto.createHash("md5").update(id).digest("hex").slice(0, hashSuffixLength)
    return `${id.slice(0, prefixMaxLength)}${separator}${hash}`
}
// ORDER MATTERS: sanitize characters BEFORE truncating, so the suffix survives validation too
```

**Flow:** inbound id → replace invalid chars with `_` → if still over 64 chars, cut to 55 and append `_` + first 8 hex of MD5 of the FULL original id → result used for every subsequent tool_result pairing.
**Invariant:** Sanitize-then-truncate ordering guarantees the final id passes the charset check; distinct long ids stay distinct because their full-length hashes differ even when prefixes collide; deterministic (same input ⇒ same output) so history replay reproduces identical ids.
**Probe:** `src/utils/__tests__/tool-id.spec.ts` (:4-25 passthrough matrix incl. MCP-prefixed real-world ids :60-78, :98 ">64 truncated", :104 determinism, :111 distinctness, :119 prefix+hash shape).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "sanitizeToolUseId truncateOpenAiCallId call_id", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt verbatim — three pure functions, no host coupling. The subtle part a porter gets wrong is order-of-operations and keeping the hash computed over the ORIGINAL id (not the sanitized one) to preserve distinctness.
