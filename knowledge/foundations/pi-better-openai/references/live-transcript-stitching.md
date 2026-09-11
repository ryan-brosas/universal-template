<!-- capsule-v2 -->
# Incremental transcript stitching — how do you merge streaming partial transcripts into stable per-turn text without duplicates?

**Source:** pi-better-openai MIT `main@86814e9047996abba08e4c907e23286329196fe0`; Codebase Memory `pi-better-openai`. **Question:** What merge rules turn `*.transcript.added` partials plus a final `turn.done` into deduplicated, turn-numbered transcripts for both roles?

## Transcript merger
**Path/Symbol:** `src/live/controller.ts:#addTranscript` (:396-416), `#finishTranscript` (:418-430), `#storeTranscript` (:437-457); per-role state (text/final/turn counters) :141-148.
**Signature:** private `(role: "user"|"assistant", text: string): void`; emitted shape `{role, turn, text, final}`.
**Data Shape:** Per role: current string + wasFinal flag + monotonic turn number; emissions suppressed when identical to last emit.

### Decisive source
```ts
// #addTranscript core ladder:
if (!current)            { startTurn(); next = text; }
else if (wasFinal) {
  if (text === current || current.endsWith(text)) return;   // echo of finished turn
  startTurn(); next = text;                                  // genuinely new turn
}
else if (text.startsWith(current)) next = text;   // growth — replace
else if (current.endsWith(text))   next = current;// re-transmission — keep
else                              next = current + text;  // disjoint append

// #finishTranscript keeps the longer streamed text when it already extends the final:
const next = !wasFinal && current.startsWith(text) && current.length > text.length ? current : text;
```

**Flow:** added-events grow/replace/append per the four-way ladder → done-event seals the turn (keeping longer streamed content) → store normalizes+trims and suppresses no-op emissions.
**Invariant:** Turn numbers advance ONLY on a true new-turn boundary (empty→first or final→different text); duplicate/re-transmitted fragments never double-print; the four-way classification is order-dependent — checking startsWith before endsWith before concat is load-bearing.
**Probe:** `tests/live-controller.test.ts` (transcript stitching scenarios through controller callbacks).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-better-openai", query: "addTranscript finishTranscript storeTranscript", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-way incremental ladder + final-vs-streamed length rule. Adapt role names and emission debouncing. Omit the pi-specific transcript UI plumbing.
