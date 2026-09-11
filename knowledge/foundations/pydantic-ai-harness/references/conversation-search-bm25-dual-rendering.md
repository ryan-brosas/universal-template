<!-- capsule-v2 -->
# Conversation search BM25: dual index/display rendering with ordinal-poisoning guards

## Source / Question
`pydantic_ai_harness/conversation_search/_toolset.py` — How do you give a model a recall tool over persisted history where the ranking corpus and the shown excerpt can have DIFFERENT truncation without terms past the display cutoff becoming unfindable — and without letting rendering artifacts (line ordinals, binary blobs) poison the index? Porters render once and either truncate the index (terms lost) or show untruncated dumps (context blowout).

## Path / Symbol
`conversation_search/_toolset.py` — `_format_message(message, *, truncate)` (:222–257), `_user_prompt_text` (:153–171), `_display_lines` (:265–275), `ConversationSearchToolset.search_conversation_history` (:328–401), `_bm25_rank` (:131–150), constructor validation (:302–313), `_load_sections` (:403–424).

## Signature
```python
def _format_messages(messages: list[ModelMessage], *, truncate: bool) -> list[str]
    # called TWICE per run section:
index_lines   = _format_messages(messages, truncate=False)  # BM25 corpus
display_lines = _display_lines(messages)                    # [i] prefix + 500-char excerpts
```

## Data Shape
One document per message line (`User: …`, `Assistant: …`, `Tool Call [name]: {args}`, `Tool [name]: return`, `Retry [name]: …`, `Speech [speaker]: transcript`). Display lines get `[index]` prefixes; results are `[score: N | run: <id> | conversation: <id>]` headers plus ±`context_lines` numbered excerpt windows joined by `\n\n---\n\n`.

### Decisive source
1. **Dual rendering** (:369–379): "Rank on the untruncated rendering so terms past the display cutoff stay findable, then show the truncated rendering." Documents stay index-aligned across flattened sections; context windows never cross a section boundary.
2. **Ordinal poisoning** (`_display_lines` :265–275): "The `[index]` prefix lives only here, not in the indexed rendering: BM25 would otherwise treat each ordinal as a rare, high-IDF token, letting a numeric query match a message by position instead of content." Empty renders become `[no text content]` so excerpts show no bare blanks.
3. **Binary exclusion** (`_user_prompt_text` :153–171): only `str`/`TextContent` items enter the corpus — str()-ing whole content would fold a BinaryContent's byte dump into BM25 ("a 70 KiB image renders as hundreds of thousands of escaped-byte characters").
4. **Unknown-part degrade** (:210–219): a part newer than this code contributes nothing at runtime; `assert_never` sits under `TYPE_CHECKING` so upstream additions fail typecheck but never crash a user's upgraded run.
5. **Tuning validation** (:306–313): negative k1 can zero the score denominator; nan/inf slip ordering checks (`nan < 0` is false) so k1 requires `math.isfinite`; b is clamped to [0,1].

## Flow / Invariant
Load sections (scope-filter runs) → flatten index lines with `(section_idx, line_idx)` locations → rank → for each match until `max_matches`: emit window `[max(0,i-ctx), min(len, i+ctx+1)]` and mark the WHOLE window `shown` so an overlapping neighbor match is skipped, not repeated. Invariants: ranking uses full-length text, display uses capped text, ordinals never indexed, one window per overlapping match cluster, `score > 0` filter keeps zero-IDF noise out.

## Probe (direct test)
`tests/conversation_search/test_conversation_search.py`: `test_user_and_text_parts_truncate_but_stay_searchable` (:639 — truncation vs findability), `test_index_prefix_is_not_a_searchable_token` (:720 — ordinal poisoning), `test_overlap_skip_backfills_lower_ranked_matches` (:740), `test_negative_k1_would_have_divided_by_zero` (:774), `test_invalid_tuning_is_rejected` (:754), `test_rendering_covers_all_part_types` (:578).

## Retrieve
`search_graph --project pydantic-ai-harness --query 'search_conversation_history bm25_rank _display_lines truncate'`

## Verdict
**Adopt** the dual-rendering contract for any search-over-history tool: index rich, display poor, keep them index-aligned. **Adopt** the ordinal/binary poisoning guards verbatim. **Adapt** the BM25 params (defaults k1=1.5, b=0.75) and the excerpt caps to your budget.
