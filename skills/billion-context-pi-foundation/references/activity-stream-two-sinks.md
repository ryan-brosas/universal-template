<!-- capsule-v2 -->
# Delegate activity stream — which events go to the live activity file, how are accumulated tool updates deduped, and what does the child never see?

**Source:** billion-context-pi (MIT) `master@6a88c5565355baebccfaf27398a6008fe08619ed`; Codebase Memory project `mnt-hdd-utopia-inspo-billion-context-pi`. **Question:** How does a parent render a background agent's progress (tools, thinking, retries, usage) for a human watching a file, without that file ever becoming model context?

## parseEventLine → activityLines: one vocabulary, two sinks
**Path/Symbol:** `src/delegate-events.ts` (304L at pin): event union `ParsedEvent` (:106-123; eleven kinds incl. `usage-update` and `agent-settled`), `ThinkingCollector` (:134-163), `parseEventLine` (:179-249), `formatArgs` (:252-262), `extractContentText` (:264-272), `activityLines` (:276-295), `newPortion` (:297-304).
**Signature:** `parseEventLine(line) -> ParsedEvent | null`; `activityLines(ev, {showThinking}) -> string[]` (each with trailing `\n`); `newPortion(text, prev) -> string`; `class ThinkingCollector { push(delta); flush() -> string }`.
**Data Shape:** child wire events (`message_update.assistantMessageEvent.{text_delta,text_end,thinking_delta,thinking_end}`, `tool_execution_start/update/end`, `auto_retry_start/end`) map to the internal union; unknown shapes return null (never throw).

### Decisive source
```ts
// src/delegate-events.ts:297-304 — partialResult is an ACCUMULATED snapshot
/**
 * partialResult is an accumulated snapshot (not a delta), so each update
 * carries everything so far. Return only the newly-appended portion.
 */
export function newPortion(text: string, prev: string): string {
  if (text.startsWith(prev)) return text.slice(prev.length);
  return text;
}
// :252-256 — bash commands read as the command string; everything else as JSON
if (typeof a.command === "string") return a.command;
```

**Flow:** per line → JSON.parse (null on failure — partial lines from chunk boundaries are handled by the caller's newline buffering) → map known shapes → applier routes: reply deltas/complete → reply file; tool-start `[tool] name args`, tool-update (deduped via newPortion against the last snapshot per callId), tool-end `[done] name (error)?`, retry lines `[retry] attempt N/M, backoff Xms — msg`, thinking (buffered per segment, flushed as ONE `[thinking] …\n` line at segment end, gated by showThinking; usage-update events are routed to the collector's `onUsage` hook, never to either file) → ACTIVITY file. The child is told ONLY the activity path; the `.out` reply path travels with the completion result (:719-724 of delegate-tool).
**Invariant:** (1) the activity file is for HUMANS — it never enters any model context, so verbosity there is free while the reply file stays pure; (2) tool updates are snapshots, not deltas — appending them raw duplicates output; prefix-slice dedup with a full-text fallback on non-prefix snapshots is mandatory; (3) parsing is total: malformed/unknown lines yield null and are dropped, never crashing the reader mid-stream.
**Probe:** `tests/events.test.ts` (whole suite: parseEventLine shapes + activityLines formatting); `tests/delegate-event-applier.test.ts:140` ("tool activity goes to activity file, not reply", asserts `[tool] bash echo hi`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-billion-context-pi", query: "parseEventLine newPortion extractContentText activityLines ThinkingCollector", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-sink split (human activity vs machine reply) and snapshot-dedup rule for any streamed-child UI. Adapt the wire-event names to your host's protocol. Omit the bash-command special case unless your tool args carry a `command` field worth showing raw.
