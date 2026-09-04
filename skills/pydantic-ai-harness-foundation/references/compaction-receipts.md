<!-- capsule-v2 -->
# Compaction receipts: deterministic secondhand-memory markers with handle discovery

## Source / Question
`pydantic_ai_harness/compaction/_receipts.py` (+ wiring in `_sliding_window_compaction.py`/`_summarizing_compaction.py`) — After a strategy crosses a compaction BOUNDARY (history summarized or dropped), how does the model learn its memory before that point is secondhand — deterministically, de-duplicably, and with a path back to the full transcript? Porters append ad-hoc timestamps text that accumulates across compactions and gives the model no recovery path.

## Path / Symbol
`compaction/_receipts.py` — `_RECEIPT_MARKER = '[History before this point'` (:25–26), `TranscriptHandleProvider` protocol + `discover_transcript_handle` (:37–58), `format_receipt` (:66–91), `_RECEIPT_METADATA = 'pydantic-ai-harness.compaction.receipt.v1'` (:94–95), `make_receipt_part` (:98–104), `is_receipt_part` (:107–113), ContextVar scope trio `open/drain/reset` + `record_receipt` (:132–158); consumers: `_sliding_window_compaction.py:137–167`, `_summarizing_compaction.py:457`.

## Signature
```python
format_receipt(*, dropped_messages: int, dropped_tokens: int, by: str,
               handle: str | None, has_summary: bool = True) -> str
# -> '[History before this point (N messages, ~M tokens) was summarized by {by}. '
#    'The summary above is secondhand; re-verify critical facts against primary sources.'
#    ' Persisted run handle: {handle}.]'
make_receipt_part(text) -> UserPromptPart(content=[TextContent(text, metadata=_RECEIPT_METADATA)])
```

## Data Shape
One receipt `UserPromptPart` appended to surviving history. Metadata key makes the part model-invisible-as-marker but machine-detectable for de-accumulation. `ReceiptInfo(strategy, dropped_messages, dropped_tokens, by, handle)` flows through an async-context-local list onto the OTel span as `compaction.receipt` events.

### Decisive source
1. **No timestamp** (:4–8): the receipt is "a pure function of its inputs" so bytes are deterministic and testable.
2. **Honest survival split** (:80–89): `has_summary=True` ⇒ "was summarized by … The summary above is secondhand"; drop-only strategies say "That context is no longer in the window" — the caveat differs because what survives differs.
3. **Handle discovery** (:48–58): capabilities implementing `compaction_transcript_handle()` are discovered from `RunContext.capabilities`; first non-None wins (`StepPersistence` returns its run_id). A non-provider capability in the dict is skipped silently (:2908 test).
4. **De-accumulation**: sliding-window compaction strips prior receipts via metadata marker BEFORE re-appending one, and reserves one token of budget for it (`find_safe_cutoff(messages, keep - int(self.receipts))` :140). Only receipt-SHAPED parts are removed — look-alike prose survives (`test_only_receipt_shaped_parts_are_de_accumulated` :2873).
5. **Marker vs content**: exact text is shipped minimal/neutral pending benchmark eval; mechanism (presence, determinism, discovery, span event) lands gated behind each strategy's `receipts=False` flag.

## Flow / Invariant
Strategy compacts → `record_receipt(ReceiptInfo…)` into the open scope → appends formatted receipt part → `compact_with_span` drains receipts into span events. Invariants: ≤1 receipt in history at any time; receipt text never varies run-to-run for equal inputs; handle appears ONLY when a provider is present and discoverable.

## Probe (direct test)
`tests/compaction/test_compaction.py`: `TestReceipts::test_only_receipt_shaped_parts_are_de_accumulated` (:2873), handle matrix :2904–2917 (`no capabilities` / `empty dict` / `non-provider capability` / `provider ⇒ 'Persisted run handle: found.'`), `TestSummarizingReceipts::test_receipt_present_and_after_summary` (:2939), `'was summarized by gpt'` assertion (:2955).

## Retrieve
`search_graph --project pydantic-ai-harness --query 'format_receipt make_receipt_part discover_transcript_handle record_receipt'`

## Verdict
**Adopt** the deterministic receipt + metadata-marker de-accumulation for ANY history rewrite a model must be told about. **Adopt** capability-protocol handle discovery over hard-wiring persistence. **Adapt** wording per your eval rig; keep the pure-function property.
