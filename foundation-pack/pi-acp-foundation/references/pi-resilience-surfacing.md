<!-- capsule-v2 -->
# Pi resilience surfacing — auto-retry / auto-compaction as plain message chunks

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** How do you surface an agent's internal resilience lifecycle (retries, context compaction) to a protocol client without inventing new protocol types — and what does the message formatter owe malformed telemetry?

## Resilience lifecycle → agent_message_chunk
**Path/Symbol:** `src/acp/session.ts` `handlePiEvent` cases `auto_retry_start`/`auto_retry_end`/`auto_compaction_start`/`auto_compaction_end` (:921-957) + `formatAutoRetryMessage` (:1192-1205).
**Signature:** `function formatAutoRetryMessage(ev: PiRpcEvent): string`.
**Data Shape:** pi emits `auto_retry_start` carrying `{attempt, maxAttempts, delayMs}` (all untrusted, possibly wrong-typed); the adapter answers with `sessionUpdate: 'agent_message_chunk'` whose content is `{type:'text', text}` — no new SessionUpdate variant, no `_meta`.

### Decisive source
```ts
case 'auto_retry_start': {
  this.emit({
    sessionUpdate: 'agent_message_chunk',
    content: { type: 'text', text: formatAutoRetryMessage(ev) } satisfies ContentBlock
  })
  break
}
case 'auto_compaction_start': {
  this.emit({ sessionUpdate: 'agent_message_chunk',
    content: { type: 'text', text: 'Context nearing limit, running automatic compaction...' } })
  break
}
```
```ts
function formatAutoRetryMessage(ev: PiRpcEvent): string {
  const attempt = Number((ev as any).attempt)
  const maxAttempts = Number((ev as any).maxAttempts)
  const delayMs = Number((ev as any).delayMs)
  if (!Number.isFinite(attempt) || !Number.isFinite(maxAttempts) || !Number.isFinite(delayMs)) {
    return 'Retrying...'                                   // malformed telemetry -> generic text
  }
  let delaySeconds = Math.round(delayMs / 1000)
  if (delayMs > 0 && delaySeconds === 0) delaySeconds = 1  // sub-second delay never renders as "waiting 0s"
  return `Retrying (attempt ${attempt}/${maxAttempts}, waiting ${delaySeconds}s)...`
}
```

**Flow:** pi's resilience events arrive as ordinary PiRpcEvents inside `handlePiEvent`; each maps to a plain text chunk through the same ordered `lastEmit` chain as streaming deltas, so a retry notice interleaved with `text_delta` events keeps its sequence position. `auto_retry_end` / `auto_compaction_end` emit fixed closing sentences ("Retry finished, resuming." / "Automatic compaction finished; context was summarized to continue the session."). `agent_start`/`turn_end`/`agent_end` are deliberately silent — the ACP turn stays open until `agent_settled` (owned by turn-state-machine.md).
**Invariant:** the resilience lifecycle NEVER introduces a new protocol type or metadata field — it rides the text channel, so any ACP client renders it; the formatter is total (every input yields a string) and a positive sub-second delay rounds UP to 1s so the client never sees "waiting 0s"; ordering with streaming text is preserved by the shared emit chain, not by the resilience branch.
**Probe:** `test/component/session-events.test.ts` — "emits agent_message_chunk for auto_retry_start with attempt/maxAttempts and rounded delay" (2400ms → "waiting 2s"), "formats a positive sub-second auto_retry_start delay as waiting 1s" (delayMs:1 → "waiting 1s"), "falls back to a generic retry message when auto_retry_start fields are missing or malformed" (attempt:'oops', maxAttempts:null, delayMs:'bad' → "Retrying..."), "omits raw errorMessage content from surfaced auto_retry_start status text", "emits agent_message_chunk for auto_retry_end", "emits agent_message_chunk for auto_compaction_start", "emits agent_message_chunk for auto_compaction_end", "preserves ordering when auto_retry_start is interleaved with text_delta events".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "formatAutoRetryMessage auto_retry_start auto_compaction_start", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt lifecycle-as-text-chunk surfacing with a total formatter and the sub-second round-up. Adapt the fixed sentences and event names to your agent's resilience vocabulary. Omit the structured `_meta` channel for retry telemetry unless your client renders progress UI from metadata.
