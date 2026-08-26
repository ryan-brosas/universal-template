<!-- capsule-v2 -->
# Session-index bloat guards — drop tool_result text at parse, cap per-message bytes with head+tail truncation (#187)

**Source:** pi-hermes-memory (MIT, `main@71beae8a`); Codebase Memory `pi-hermes-memory`. **Question:** The session SQLite index doubles as search corpus — how do you stop unbounded tool output and future large content blocks from ballooning the database?

## truncateMessageContent + tool_result exclusion
**Path/Symbol:** `src/store/session-indexer.ts:truncateMessageContent` (:41–53, exported for tests), applied at insert :104 (`truncateMessageContent(msg.content)`); constant `DEFAULT_MAX_MESSAGE_CONTENT_LENGTH = 100 * 1024` (`src/constants.ts` :23–28, doc comment: "Tool results are excluded during parsing, but this cap also protects the database from unexpected large text blocks in future Pi content formats"). Parallel parse-side exclusion: `session-indexer.ts:extractTextContent` case `tool_result` (:153–160) and `src/store/session-parser.ts` :65–72 — both now EMPTY cases with rationale comments ("Tool calls are indexed separately… adds bloat without improving session search").
**Signature:** `truncateMessageContent(content: string, maxLength = DEFAULT_MAX_MESSAGE_CONTENT_LENGTH): string`.
**Data Shape:** over-limit content → `prefix + "\n... (truncated, ${content.length} chars total)\n" + suffix` where prefix = `ceil((maxLength - notice.length)/2)`, suffix = `floor(.../2)` — the notice is INSIDE the budget.

### Decisive source
```ts
export function truncateMessageContent(content, maxLength = DEFAULT_MAX_MESSAGE_CONTENT_LENGTH) {
  if (content.length <= maxLength) return content;
  const notice = `\n... (truncated, ${content.length} chars total)\n`;
  const retainedLength = Math.max(0, maxLength - notice.length);
  const prefixLength = Math.ceil(retainedLength / 2);
  const suffixLength = Math.floor(retainedLength / 2);
  const suffix = suffixLength > 0 ? content.slice(-suffixLength) : '';
  return `${content.slice(0, prefixLength)}${notice}${suffix}`;
}
```

**Flow:** JSONL parse drops tool_result text entirely (tool NAMES live in the separately indexed tool_calls JSON) → any surviving message over 100 KiB is split head+tail around a self-describing notice → stored row never exceeds the cap regardless of upstream content-format changes.
**Invariant:** both ends matter — file/command output usually carries its conclusion in the TAIL (error summary after a long dump), so suffix-reserved truncation beats prefix-only. The stored size stays deterministic: notice length is subtracted before splitting, so the result can never overshoot `maxLength`. Exclusion happens at PARSE (never indexed), capping at WRITE (defense in depth for unknown block types).
**Probe:** `npx tsx --test tests/store/session-indexer.test.ts` — "should cap oversized message content while retaining both ends" (:86, stored content matches `/truncated, \d+ chars total/`, and `truncateMessageContent('short content') === 'short content'`). GREEN under `npx tsx --test`.
**Retrieve:** `search_graph({ project: "pi-hermes-memory", query: "truncateMessageContent extractTextContent tool_result", limit: 5 })`

## Verdict
Adopt parse-level exclusion of known-bloat block types plus a defensive whole-row cap with head+tail retention. Adapt the cap constant to your storage budget. Pair with `session-indexer.md` (index mechanics) and `bounded-tool-output.md` (the display-side budget this complements).
