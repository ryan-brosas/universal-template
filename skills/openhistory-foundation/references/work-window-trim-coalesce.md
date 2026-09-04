<!-- capsule-v2 -->
# Work-window trim + adjacent-context coalescing — how do you shrink a raw event window to the evidence that matters before summarization?

**Source:** OpenHistory MIT `main@daf7b073ce93673d0453d9f69b7435224c4bf49c`; Codebase Memory `openhistory`. **Question:** Which context events survive into an episode, and when do repeated passive events collapse?

## prepareEpisodeEvents + compactAdjacentContextEvents
**Path/Symbol:** `src/main/episode-segmenter.ts:prepareEpisodeEvents` (lines 121-139) and `compactAdjacentContextEvents` (141-164) with `eventFingerprint` (204-214).
**Signature:** `prepareEpisodeEvents(events: ActivityEvent[], contextLeadMs: number): ActivityEvent[]`; `compactAdjacentContextEvents(events): ActivityEvent[]`.
**Data Shape:** episode event buffer in; trimmed/coalesced array out (empty ⇒ caller drops the episode); dedup horizons per kind: `application_activated` 60 s, `window_changed` 10 s, `focused_element_changed` 5 s, `ui_snapshot` 60 s, `application_terminated` 10 s.

### Decisive source
```ts
let startIndex = firstWorkIndex;
while (startIndex > 0 && firstWorkTime - Date.parse(events[startIndex - 1]!.timestamp) <= contextLeadMs)
  startIndex -= 1;
let endIndex = lastWorkIndex;
if (["screen_slept", "session_locked"].includes(events[lastWorkIndex + 1]?.kind ?? "")) endIndex += 1;
return compactAdjacentContextEvents(events.slice(startIndex, endIndex + 1));
...
const horizon = horizons[event.kind];
if (previous && horizon !== undefined &&
    eventFingerprint(previous) === eventFingerprint(event) &&
    Date.parse(event.timestamp) - Date.parse(previous.timestamp) <= horizon)
  continue;   // drop the LATER duplicate
```

**Flow:** locate first/last work-evidence index → walk back from first work event while gap ≤30 s (bounded lead, not unbounded context) → optionally keep one trailing sleep/lock terminator → collapse consecutive identical-fingerprint events inside per-kind time horizons, keeping the EARLIEST occurrence.
**Invariant:** trimming never crosses below the first work event beyond the lead budget; an episode with zero work events yields `[]` and is discarded by flush (`if (prepared.some(isWorkEvent))`). Fingerprint equality is full-payload JSON (`kind`, app key, title, element, visibleText, browser, document) — same kind with different content is never coalesced.
**Probe:** `src/main/episode-segmenter.test.ts:154-178` — executed GREEN at pin: stale activation before work is trimmed while the id matches the lone-work-event segmentation; immediate duplicate collapses to one event; identical activations across a 45-s collector restart coalesce ("before", "activation-one", "after").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openhistory", query: "prepareEpisodeEvents compactAdjacentContextEvents fingerprint", limit: 10 });
```
Executed live byte-for-byte: all three cited symbols return as the top `episode-segmenter` rows; no unrelated module outranks them.

## Verdict
Adopt evidence-anchored windowing with a bounded context lead and fingerprint-keyed per-kind coalesce horizons; adapt the horizon table and work-kind set to your telemetry vocabulary; omit the sleep/lock terminator special case if your stream has no system-boundary kinds. Coverage: `no_recorded_issue` on `src/main/episode-segmenter.ts`; probe suite executed green at pin.
