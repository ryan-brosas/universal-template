<!-- capsule-v2 -->
# JSON event-stream child parsing — how is a delegate's newline-delimited stdout turned into reply text plus activity lines?

**Source:** billion-context-pi (MIT) `master@6a88c5565355baebccfaf27398a6008fe08619ed`; Codebase Memory project `mnt-hdd-utopia-inspo-billion-context-pi`. **Question:** How must a porter parse `--mode json` child output so the final answer survives even when deltas are missing, truncated, or the child dies mid-stream?

## Pure parse functions + delta/tail accumulator + snapshot-dedup for updates
**Path/Symbol:** `src/delegate-events.ts` (304L at pin): `parseEventLine` (:179-249), `newPortion` (:297-304), `extractContentText` (:264-272), `activityLines` (:276-295), `ThinkingCollector` (:134-163). Event union `ParsedEvent` (:106-123) now carries ELEVEN kinds — the original nine plus `usage-update` (`UsageUpdateEvent`) and `agent-settled` (`AgentSettledEvent`, fed by the watchdog's settledGrace); `parseEventLine` maps `message_end` → usage (:242-244) and `agent_settled` (:245-247).
**Signature:** `parseEventLine(line: string): ParsedEvent | null`; `newPortion(text: string, prev: string): string`; discriminated union over tool-start/update/end, reply-delta/complete, thinking-delta/end, retry-start/end, usage-update, agent-settled.
**Data Shape:** events arrive as `{type:"message_update", assistantMessageEvent:{type:"text_delta"|"text_end"|…}}`, top-level `tool_execution_*` / `auto_retry_*` / `message_end` / `agent_settled`; non-JSON and unknown types → null (never throw).

### Decisive source
```ts
// delegate-events.ts:297-304 — partialResult is a SNAPSHOT, not a delta:
// "partialResult is an accumulated snapshot (not a delta), so each update
// carries everything so far. Return only the newly-appended portion."
export function newPortion(text: string, prev: string): string {
  if (text.startsWith(prev)) return text.slice(prev.length);
  return text;
}
```

**Flow:** per line: JSON.parse guarded → map to typed event → reply path appends deltas AND treats `text_end.content` as a tail-fill (the applier writes only the missing suffix — "final content arrives via text_end with no deltas — never lost"; "text_end fills the missing tail"; "no duplicate write" when shorter than written deltas) → tool activity formatted into `[tool]/[done]/[retry]` activity-file lines while thinking goes through ThinkingCollector, gated by showThinking.
**Invariant:** the reply file must converge to exactly the final text under ALL four stream shapes: normal deltas; text_end-only (killed process before first delta); truncated deltas; delta-without-text_end (child dies — keep what streamed). Snapshot-vs-delta confusion double-writes; treating text_end as authoritative overwrite loses interleaved ordering.
**Probe:** `tests/delegate-event-applier.test.ts:44-141`: normal streaming (:44), text_end-only bug repro (:53), truncated fill (:60), multi-turn file (:68), empty writes (:89), killed-process keep-delta (:97), thinking never pollutes reply file (:105), no-duplicate-write (:125), omp appendRaw fallback (:133), tool→activity not reply (:140).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-billion-context-pi", query: "parseEventLine newPortion activityLines ThinkingCollector", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-shape convergence contract + snapshot dedup verbatim — it is pinned by a dedicated test suite per shape. Adapt the event type vocabulary to your host's wire format. Omit bash-command special-casing in formatArgs if your tools don't carry command strings.
