<!-- capsule-v2 -->
# Delegate event applier — how do streamed child deltas and an authoritative text_end merge into one reply file without losing or duplicating text?

**Source:** billion-context-pi (MIT) `master@6a88c5565355baebccfaf27398a6008fe08619ed`; Codebase Memory project `mnt-hdd-utopia-inspo-billion-context-pi`. **Question:** When a delegate's stdout streams `text_delta` tokens but only `text_end` carries the authoritative block content, how must the applier write the reply so a truncated stream is healed yet a fully-streamed one is never duplicated?

## makeEventApplier: delta-accumulate + tail-backfill on reply-complete
**Path/Symbol:** `src/delegate-tool.ts`: `makeEventApplier` (:239-312; reply-complete branch :278-291); event vocabulary from `src/delegate-events.ts` (`parseEventLine` :179-249).
**Signature:** `makeEventApplier({ showThinking, onUsage?, onSettled? }, { reply, activity }) -> { handleEventLine(line), getReplyText(), appendRaw(text) }`.
**Data Shape:** two writers (reply stream = future result file; activity stream or null on non-json hosts); internal ledger `msgWritten` counts chars already streamed for the CURRENT message; `lastToolText` Map keyed by toolCallId; `replyText` holds the last completed turn's content.

### Decisive source
```ts
// src/delegate-tool.ts:278-291 — the whole contract in one branch
if (ev.kind === "reply-complete") {
  flushThinking();
  const tail = ev.content.slice(msgWritten);
  if (tail) {
    writers.reply.write(tail);            // heal a truncated stream
    debug.event("reply-complete-tail", {...});
  }
  if (ev.content.length < msgWritten) {
    logWarn("delegate", { event: "reply-content-shorter-than-delta", ... }); // NEVER truncate back
  }
  msgWritten = 0;
  replyText = ev.content;                 // replyText = LAST turn's content only
}
```

**Flow:** `text_delta` → flush thinking → append to replyText AND write through immediately (`msgWritten += delta.length`) → `text_end` → write only `content.slice(msgWritten)` (empty when deltas covered everything) → reset `msgWritten=0`, set `replyText=content`. Multi-turn children: the FILE accumulates every turn ("first turnsecond turn"), while `getReplyText()` returns only the last turn — the finalize path reads `applier.getReplyText().trim()` (:790, inside `finalize` :782-853) and falls back to stderr/placeholder when empty. Thinking deltas buffer in `ThinkingCollector` and flush as one `[thinking] …\n` line into ACTIVITY only, gated by `showThinking`; they never touch the reply file. `tool-update` events are accumulated snapshots — `newPortion(text, prev)` strips the prefix already written.
**Invariant:** (1) the reply file never duplicates streamed content nor loses unstreamed tails — slice-based backfill, never overwrite; (2) if `text_end` is SHORTER than what was written (provider regression), keep the longer file and warn — never rewrite history; (3) a killed process that emitted only deltas keeps its partial file (there is no truncation-on-death).
**Probe:** `tests/delegate-event-applier.test.ts:44` (deltas cover full content, end adds nothing), `:53` (end-only "final answer" never lost), `:60` (truncated stream tail-filled), `:125` (shorter-than-deltas: no duplicate write, replyText="short" but file stays "longer"), `:105` (thinking never pollutes reply; activity gated).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-billion-context-pi", query: "makeEventApplier replyText msgWritten", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the delta-ledger + tail-backfill protocol verbatim for any host whose streaming API sends a final authoritative payload after incremental deltas. Adapt event names (`message_update.assistantMessageEvent.*`) to your transport. Omit the omp raw-stdout passthrough (`appendRaw`) unless you have the same no-event-mode fallback host.
