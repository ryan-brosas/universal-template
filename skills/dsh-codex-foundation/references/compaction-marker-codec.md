<!-- capsule-v2 -->
# Native compaction marker codec — carry opaque provider output through text checkpoints and restore it losslessly

**Source:** dsh-codex Apache-2.0 main@e3e54e206f7c829503c7e6eed378643ba0416792; Codebase Memory dsh-codex. **Question:** how do you durably frame provider-native opaque output inside a host text checkpoint so it survives history persistence and expands back to native items without corruption?

## nativeCompactionMarker / markerOutput / expandNativeCompactionMarkers
**Path/Symbol:** src/responses.ts:99-141 (encode 99-104, decode 107-118, expand 121-141); versioned tags at 26-27.
**Signature:** nativeCompactionMarker(output: readonly unknown[]): string; markerOutput(text: string): readonly unknown[] | undefined; expandNativeCompactionMarkers(input: readonly unknown[]): unknown[].
**Data Shape:** Markers are literal tags <dsh-openai-codex-compaction-4f5cf1b7-v1> … </…v1> framing JSON.stringify(output). Valid payloads contain at least one item {type:'compaction'}. Expansion scans user-role messages whose content array holds an input_text block and swaps the whole message for the carried items.

### Decisive source
~~~ts
function nativeCompactionMarker(output: readonly unknown[]): string {
  if (!output.some(item => isRecord(item) && item['type'] === 'compaction')) {
    throw new Error('OpenAI Codex compact response did not contain a compaction item')
  }
  return COMPACTION_MARKER_OPEN + JSON.stringify(output) + COMPACTION_MARKER_CLOSE
}

function markerOutput(text: string): readonly unknown[] | undefined {
  const start = text.indexOf(COMPACTION_MARKER_OPEN)
  if (start < 0) return undefined
  const payloadStart = start + COMPACTION_MARKER_OPEN.length
  const end = text.indexOf(COMPACTION_MARKER_CLOSE, payloadStart)
  if (end < 0) return undefined
  const parsed: unknown = JSON.parse(text.slice(payloadStart, end))
  if (!Array.isArray(parsed) || !parsed.some(item => isRecord(item) && item['type'] === 'compaction')) {
    throw new Error('OpenAI Codex native compaction checkpoint is malformed')
  }
  return parsed
}
~~~

**Flow:** encode validates the compaction item exists then frames the JSON between versioned tags as assistant text → the host persists that text like any message → on the next request every user message content is scanned; the first complete framed marker is decoded, revalidated, and the entire user message is replaced by the carried items; messages without a complete valid marker pass through untouched.
**Invariant:** both directions validate for the compaction item (fail closed); a partial or truncated marker decodes to undefined rather than garbage; ordinary user text is never rewritten; the JSON round-trip preserves the opaque encrypted payload exactly; the tag embeds a version suffix so format changes cannot silently mix generations.
**Probe:** tests/codex-compaction.spec.ts:221-322 — native compact output becomes a durable checkpoint and the follow-up request input equals restored user item + compaction item + new message; executed via pnpm test -- tests/codex-compaction.spec.ts.

## Get live surrounding code
**Retrieve:**
~~~ts
await mcp.codebase_memory.search_graph({ project: 'dsh-codex', qn_pattern: 'dsh-codex\\.src\\.responses\\.(nativeCompactionMarker|markerOutput|expandNativeCompactionMarkers)', limit: 10, fields: ['signature', 'name', 'file', 'lines'] });
~~~

## Verdict
Adopt validate-on-write plus validate-on-read framing with a versioned tag and whole-message replacement semantics for any host that flattens provider-native state into portable text. Adapt tag naming and the sentinel item type to the target protocol. Omit the Codex-specific compaction item schema. Coverage no_recorded_issue + metadata_match for src/responses.ts and tests/codex-compaction.spec.ts; malformed-marker branches are source-confirmed (the direct suite exercises the happy path end to end).
