<!-- capsule-v2 -->
# Zero-cost compaction kit: clamp-oversized-part, clear-tool-results cache gate, dedup file reads

## Source / Question
`pydantic_ai_harness/compaction/_clamp_oversized_messages.py`, `_clear_tool_results.py`, `_deduplicate_file_reads.py` (+ `_report_context_usage.py`) — How do you reclaim context with ZERO LLM calls without corrupting history validity, provider prompt caches, or live data? Three distinct traps: the runaway generation no window-strategy can fix; clearing that busts the cache for a trivial gain; dedup that drops a still-live read.

## Path / Symbol
`_clamp_oversized_messages.py` — `ClampOversizedMessages` (33–189): `_CLAMP_MARKER` (18–20), `_CLAMP_ARGS_KEY = '_clamped'` (24–27), `_clamp` (124–133), `compact` (135–172, exact-type check at :157–166); `_clear_tool_results.py` — `ClearToolResults` (31–148): pair selection (:128–129), `min_clear_tokens` gate (:144–147); `_deduplicate_file_reads.py` — `DeduplicateFileReads`: mandatory `file_key` seam (no default — "a wrong guess would drop live data" :36–38), latest-wins blanking; `_report_context_usage.py` — `ReportContextUsage`/`ContextUsage` observation-only reading w/ `resolved` flag.

## Signature
```python
def _clamp(self, text: str) -> str | None:
    head = text[:keep_head]; tail = text[-keep_tail:] if keep_tail else ''
    clamped = head + marker.format(removed=…, original=…) + tail
    return None if len(clamped) >= len(text) else clamped      # must actually shrink
# ToolCallPart args → replace(part, args={'_clamped': clamped})   # stays a JSON OBJECT
```

## Data Shape
Clamp touches ONLY `ModelResponse` parts — TextPart content and plain ToolCallPart args. Marker carries removed/original char counts. Clear replaces oldest tool-return contents with `[tool result cleared]` beyond `keep_pairs` most-recent pairs (`exclude_tools` never cleared; optional `clear_tool_inputs`). Report emits `ContextUsage(used_tokens, window_tokens, resolved)` — `resolved=False` means the denominator is the fallback registry guess.

## Decisive source
1. **Why clamp exists** (:37–47): a runaway generation makes ONE part so large the next request exceeds the cap; SlidingWindow drops the OLDEST (offender is newest), ClearToolResults only touches results, Summarizing hits the same cap. Head/tail works because degenerate output is low-entropy repetition. Request-side parts are OUT of scope (:50–53): user input is never silently rewritten.
2. **Exact-type guard on tool-call args** (:156–166): `type(part) is ToolCallPart` NOT isinstance — framework-typed subclasses (`ToolSearchCallPart`, `LoadCapabilityCallPart`) narrow `args` to a typed shape validated by `ModelMessagesTypeAdapter` on persistence restore; replacing it with the `_clamped` object "keeps the concrete class but fails the round-trip". Args stay an object (not bare string) so `args_as_json_str()` emits valid function arguments (:24–27).
3. **Shrink-or-skip** (:2095 test): a part is clamped only when oversized AND the clamp actually shrinks it — keep_head+keep_tail+marker can exceed a barely-oversized part.
4. **Cache-bust economics** (ClearToolResults :43–46): clearing rewrites content → invalidates the provider prompt cache from that point (next request pays cache-write). `min_clear_tokens` skips clears whose reclaimed estimate doesn't justify the bust — measured as before-minus-after token estimate (:144–147).
5. **Dedup identity is injected** (:34–38): file_key callable supplied per agent (e.g. `read_file` → args path); latest read keeps content, earlier ones blanked to `[superseded file read]`; pairing preserved via shared rebuild helper.

## Flow / Invariant
Clamp/clear/dedup all compose as FIRST tiers of TieredCompaction (clamp runs before clear: it's the only zero-LLM survival for runaway generations). All three share `_shared.compact_with_span` + `record_compaction_reclaim` + trigger triple. Invariants: history stays schema-valid after every rewrite (pairs intact, typed parts untouched, JSON-object args); user/system text never rewritten by zero-cost tiers; observation-only capabilities (ReportContextUsage) register AFTER compactors to see compacted history.

## Probe (direct test)
`tests/compaction/test_compaction.py`: `test_clamps_oversized_response_text` (:2038), `test_clamp_skipped_when_not_smaller` (:2095), `test_clamps_oversized_tool_call_args` (:2105), `test_tool_call_args_not_clamped_when_disabled` (:2152), `test_clamp_oversized_wired_into_agent` (:2219), `test_clear_does_not_break_tool_search_on_next_request` (:2231), `TestClearToolResults` — `test_min_clear_tokens_skips_small_gain` (:1650)/`…_proceeds_on_large_gain` (:1659), `TestDeduplicateFileReads` (:1739), span tests :2496–2591 (clamp spans only when something was clamped).

## Retrieve
`search_graph --project pydantic-ai-harness --query 'ClampOversizedMessages ClearToolResults DeduplicateFileReads'`

## Verdict
**Adopt** clamp-with-exact-type-guard for any history that persists through a typed round-trip; **adopt** min-clear-token cache economics; **adopt** injected-identity dedup (never guess file identity). **Omit** ReportContextUsage if your host has its own gauge.
