<!-- capsule-v2 -->
# Anthropic prompt-cache breakpoints — where do `cache_control` markers go so a growing chat never pays full-input price?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** When every request resends the whole conversation, which exact blocks carry `cache_control: ephemeral` so the stable prefix is cached and only the newest tail is re-billed as input?

## System block always marked; last TWO user messages marked; marker rides ON the text block
**Path/Symbol:** `src/api/transform/caching/anthropic.ts` (`addCacheBreakpoints(systemPrompt, messages)` :3-41; system overwrite :4-10; string→array coercion loop :12-17; last-two-user filter `.filter(role==="user").slice(-2)` :19-27; last-text-part picker + `"..."` filler :28-37).
**Signature:** `function addCacheBreakpoints(systemPrompt: string, messages: OpenAI.Chat.ChatCompletionMessageParam[]): void` — MUTATES `messages` in place.
**Data Shape:** Input is OpenAI-shaped messages whose `content` may be a bare string or a parts array; output marks parts with `cache_control: { type: "ephemeral" }` (Anthropic extension fields carried through OpenAI-compatible transports, hence the `@ts-ignore`).

### Decisive source
```ts
messages[0] = {
    role: "system",
    content: [{ type: "text", text: systemPrompt, cache_control: { type: "ephemeral" } }], // REBUILDS msg[0]
}
for (const msg of messages) {           // normalize ALL user strings to arrays FIRST
    if (msg.role === "user" && typeof msg.content === "string")
        msg.content = [{ type: "text", text: msg.content }]
}
messages.filter((msg) => msg.role === "user").slice(-2).forEach((msg) => {
    let lastTextPart = msg.content.filter((part) => part.type === "text").pop()
    if (!lastTextPart) {                 // image-only user message:
        lastTextPart = { type: "text", text: "..." }   // append placeholder part, mark THAT
        msg.content.push(lastTextPart)
    }
    lastTextPart["cache_control"] = { type: "ephemeral" }
})
```
Three load-bearing details a porter gets wrong: (1) the system message is REPLACED wholesale (`messages[0] = ...`) rather than annotated in place — any caller-supplied system content is overwritten by the canonical `systemPrompt`; (2) the marker attaches to the TEXT PART inside `content`, never to the message object; (3) an image-only target message gets a synthetic `{type:"text",text:"..."}` part appended and THAT is marked, because Anthropic requires a cacheable text prefix. The in-code comment documents why last-two works: this app adds one user message per turn (env details ride at the END of each user message, which also makes moving/inserting parts safe); with multiple user turns added per round you would instead mark the user message BEFORE the last assistant message.
**Flow:** rebuild system block with marker → coerce every string user content into a parts array → select the final two user messages regardless of intervening assistant/tool messages → mark each one's last text part (inserting the `...` filler when there is none).
**Invariant:** Exactly three breakpoints max per request (1 system + ≤2 user) — Anthropic's ≤4 limit stays satisfied; breakpoint positions depend ONLY on roles/order, never on token counts, so consecutive requests form a growing cacheable prefix; a user message without text still terminates a cacheable segment instead of silently dropping its breakpoint.
**Probe:** `src/api/transform/caching/__tests__/anthropic.spec.ts` — :10 system always marked, :36 single-user gets one, :49 two users get two, :67 last-two-of-many (assistant interleaved :87), :112 array-content last-text-part marking, :139 image-only `"..."` filler appended, :161 string coercion even when no breakpoint lands.
**Coverage caveat:** consumer wiring (`openrouter.ts` imports this twin for Anthropic-routed models; `vercel-ai-gateway.ts` uses its own copy) verified by grep at this pin, not by a dedicated integration spec.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "addCacheBreakpoints cache_control ephemeral system prompt last two user messages", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the placement policy verbatim (system + last-two-users, marker-on-text-part, `...` filler for image-only turns) for any Anthropic-protocol conversation client. Adapt the transport shim (here: Anthropic fields smuggled through OpenAI-shaped messages). Do NOT port the mutation-in-place signature into pipelines that reuse message arrays across retries without deep-cloning — the rebuilt `messages[0]` will silently drop caller system content.
