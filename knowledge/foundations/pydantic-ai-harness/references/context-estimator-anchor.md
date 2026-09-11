<!-- capsule-v2 -->
# Anchored context estimation: provider usage as ground truth, heuristic only for the tail

## Source / Question
`pydantic_ai_harness/compaction/_shared.py` — How do you estimate "will this history exceed the window" when character heuristics are multi-x wrong on token-dense content (minified JSON, base64, non-Latin scripts) and see NOTHING of the tool definitions a request carries? Porters sum `len(text)//4` and either compact too late (blown window) or constantly (summary churn).

## Path / Symbol
`compaction/_shared.py` — `estimate_context_tokens` (:216–265), `_latest_usage_anchor` (:273–279), `_collect_message_text` (:68–89), `_instructions_text` (:162–173), `_revealed_tool_schema_text` (:294–304), `has_context_usage_anchor` (:268–270), `estimate_token_count` (:199–213), `record_compaction_reclaim`/`get_compaction_reclaim` (:312–326), `exceeds` (:329–345).

## Signature
```python
def estimate_context_tokens(messages, tokenizer=None, *, model_request_parameters=None) -> int:
    if anchor := _latest_usage_anchor(messages):        # last ModelResponse w/ input_tokens
        anchored = message.usage.input_tokens + message.usage.output_tokens
        segments = _collect_message_text(messages[index + 1:])   # tail AFTER anchor only
        if current_instructions != _instructions_text(messages[: index + 1]):
            segments = [*segments, *current_instructions]        # changed-instructions rule
        segments.extend(_revealed_tool_schema_text(messages[index + 1:], model_request_parameters))
        return anchored + sum(len(s) for s in segments) // _CHARS_PER_TOKEN
    # else: pure heuristic over ALL text incl. latest instructions
```

## Data Shape
Input: full message sequence (+ pending request parameters for schema text). Anchor: most recent `ModelResponse` with truthy `usage.input_tokens` (zero-usage responses are NOT anchors). Output: `anchored + estimated_tail`.

### Decisive source
1. **Anchor semantics** (:222–246 docstring): the anchor's `input_tokens` "measured everything the provider was actually sent — instructions, tool definitions, and every prior message"; `output_tokens` measured its own response parts; their sum is ground truth up to that point.
2. **Changed-instructions rule** (:250–257): the anchor paid for the instructions in force at ITS request; count the current set ONLY when it differs from the anchor-era set (dynamic instructions / resumed-under-new-prompt), else you double-count.
3. **Mid-cycle rewrite honesty** (:238–245): compaction editing older messages after the anchor's request ⇒ overestimate until the next real response re-anchors; `TieredCompaction` compensates by subtracting each tier's estimated reclaim. "Compacting slightly early is the cheap failure mode."
4. **Reclaim ledger** (:312–326): ContextVar keyed by weakref to the request_context — accumulates across MULTIPLE compactors in one hook chain but ignores reclaim recorded for a DIFFERENT request context.
5. **Instructions counted once** (:162–173): every ModelRequest carries its era's instructions but a request sends ONE set — summing them would multiply the system prompt by turn count.

## Flow / Invariant
Find newest usage anchor → take its in+out tokens as-is → estimate only post-anchor text → add schemas of tools revealed after the anchor (from availability deltas matched into pending tool_defs) → add instructions iff changed. Invariants: never re-count anything the anchor already paid for; unknown part types contribute nothing rather than crashing (#577); `FilePart` binary contributes no char-count.

## Probe (direct test)
`tests/compaction/test_compaction.py::TestEstimateContextTokens`: `test_no_usage_falls_back_to_heuristic` (:186), `test_anchors_on_reported_usage` (:190), `test_counts_only_messages_after_the_anchor` (:195), `test_anchors_on_the_most_recent_usage` (:203), `test_zero_usage_response_is_not_an_anchor` (:211), `test_instructions_changed_after_the_anchor_are_counted` (:224). Reclaim: `tests/compaction/test_context_budget.py::TestReportContextUsage::test_accumulates_reclaim_from_multiple_compactors` (:909), `test_ignores_reclaim_from_a_different_request_context` (:938). Schemas: `TestProgressiveToolSchemas` (:693).

## Retrieve
`search_graph --project pydantic-ai-harness --query 'estimate_context_tokens _latest_usage_anchor record_compaction_reclaim'`

## Verdict
**Adopt** anchor-plus-tail as THE budget estimator for any agent loop against provider-reported usage. **Adopt** the changed-instructions rule and the reclaim correction for mid-run compaction. **Omit** pydantic-ai-specific part unions — port the shape, map your own part types.
