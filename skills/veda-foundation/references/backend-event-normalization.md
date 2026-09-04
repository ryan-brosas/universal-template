<!-- capsule-v2 -->
# Backend event-dialect normalization — how do three CLIs' stream events collapse into one Message union without double-counting usage?

**Source:** veda-ts MIT `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6` (v0.75.9); Codebase Memory `veda`. **Question:** What is the shared normalization skeleton every CLI backend must follow — session synthesis, usage capture, the synthetic done fallback, and the event→Message mapping table?

## parseStream skeleton + per-CLI normalizeEvent
**Path/Symbol:** identical skeleton in all three: `src/backend/pi.ts` : `parseStream` (:152-180) + `normalizeEvent` (:182-256); `src/backend/codex.ts` (:82-110 + :112-220); `src/backend/claude.ts` (:103-131 + :133-189). Shared line parser: `src/backend/util/spawn.ts` : `parseNdjsonStream` (:166-201).
**Signature:** `private async *parseStream(stream: ReadableStream<Uint8Array>): AsyncIterable<Message>` over a per-class `normalizeEvent(event: unknown): Message | null`.
**Data Shape:** unified `Message` union: init{text? sessionId} / text{content} / reasoning{content} / tool_start{toolName,toolInput} / tool_result{toolName?,toolResult} / done{sessionId?,usage{inputTokens,outputTokens,cachedTokens?,costUsd?}} / error{content}; every carried Message embeds the raw upstream event as `raw`.

### Decisive source (pi variant; codex/claude share the skeleton)
```ts
for await (const event of parseNdjsonStream(stream)) {
      const msg = this.normalizeEvent(event);
      if (msg) {
        if (msg.type === 'init' && msg.sessionId) sessionId = msg.sessionId;
        if (msg.type === 'done' && msg.usage)     usage = msg.usage;
        yield msg;
      }
    }
    if (!usage) {
      yield { type: 'done', sessionId, usage: { inputTokens: 0, outputTokens: 0 } };
    }
```
Dialect mapping highlights: pi `agent_start`→init with **synthesized** `crypto.randomUUID()` sessionId (pi JSON mode has no session_meta); pi `turn_end` carries usage while `agent_end` returns null ("agent_end signals completion but turn_end already carries usage") — emitting both would double-count; codex `thread.started`/`item.started`/`item.completed`/`turn.completed`; claude `system`/`assistant`(text-parts joined, first tool_use wins)/`user`(tool_result)/`result`. Codex wraps system prompts INLINE as `<system_instructions>…</system_instructions>` at the top of stdin (claude does the same; pi passes `--system-prompt`) because those CLIs lack a prompt-file flag.

**Flow:** raw NDJSON bytes → tolerant line parse (malformed lines SKIPPED silently, buffered tail parsed at stream end) → dialect switch → null = "structural event, drop" → yield normalized → after loop, guarantee EXACTLY one terminal done by synthesizing zero-usage done when none seen.
**Invariant:** downstream planes (ensemble usage folding, deep-think checkpoint usage seeding) may assume AT MOST one real done with usage and ALWAYS a final done message — the synthetic-done fallback is what keeps resume/usage logic total instead of optional-chained everywhere. Session ids are opaque strings (real or synthesized) usable for claude/codex `resume`; pi.resume deliberately throws 'Resume not supported'.
**Probe:** `tests/backend/pi.test.ts:105-202` (tool_start/tool_result mapping pins via `(backend as any).normalizeEvent`) + `tests/core/ensemble-retry.test.ts` (usage accumulation over the union). Run: `bun test tests/backend/pi.test.ts tests/core/ensemble-retry.test.ts`.
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"veda","query":"normalizeEvent agent_start turn_end","limit":5,"detail":"ids"}'
```
→ resolves `veda.src.backend.pi.normalizeEvent Method src/backend/pi.ts`.

## Verdict
Adopt the parseStream skeleton verbatim (esp. the synthetic-done invariant); adopt the dialect tables as reference translations when adding your own backend twins. Adapt field names to each CLI's live wire format (re-derive against real streams). Omit pi's UUID synthesis only if your CLI provides real session ids.
