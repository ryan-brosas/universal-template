<!-- capsule-v2 -->
# Sliding-window compaction — pair-safe cutoffs, pin survival, and receipt bookkeeping that reserves its own token cost

**Source:** pydantic-ai-harness (MIT) `main@c79fabc58fd3bd587dcc27f9e7d9de179d748cf0`; Codebase Memory `pydantic-ai-harness`. **Question:** how does a harness trim an oversized context window without orphaning a tool call from its result, losing pinned messages, or silently dropping work the model must know about?

## SlidingWindowCompaction mechanics
**Path/Symbol:** `pydantic_ai_harness/compaction/_sliding_window_compaction.py` (252L); helpers `_shared.py` (`find_safe_cutoff`/`find_token_cutoff`), `_pinning.py` (90L); package `__init__` export surface.
**Signature:** `SlidingWindowCompaction(max_messages | max_tokens | max_fraction, preserve_first_user_message=True, ...)` — a pydantic-ai capability hooking `before_model_request`.
**Data Shape:** triggers are mutually exclusive by validation; `max_fraction` resolves PER REQUEST from the request's model so one setting behaves on any model. Trimming runs in `before_model_request`, transparent to the rest of the run.

### Decisive source
```python
# Cutoffs are TOOL-PAIR-SAFE (find_safe_cutoff/find_token_cutoff from _shared):
# never orphan a tool call from its return.
# preserve_first_user_message=True re-prepends the first UserPromptPart after
# trimming (task context survives).
# Pinned messages (pin/is_pinned/reinject_pinned) are re-injected after any trim.
```

**Flow:** measure → pick pair-safe cutoff → trim → re-prepend first user message → re-inject pins → (opt-in) prepend a deterministic compaction receipt.
**Invariant:** a tool call and its result are never split across the cutoff; pinned content survives any trim; the receipt's OWN tokens are RESERVED from the keep-budget before computing the cutoff; prior receipt-only requests are stripped before inserting the new one; dropped messages are detected by IDENTITY (`is` comparison against survivors), never by equality.
**Probe:** `tests/compaction/test_compaction.py` (3,723L) pins mutual-exclusion triggers, pair-safe cutoffs, pin survival, and receipt emission.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-ai-harness", query: "SlidingWindowCompaction find_safe_cutoff pin receipt", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt pair-safe cutoffs, pin-honoring, and self-reserving receipts; adapt the trigger settings to the host's window-resolution; omit host-specific strategy wiring. The wider kit (`ClampOversizedMessages`, `ClearToolResults`, `DeduplicateFileReads`, `TieredCompaction`, `SummarizingCompaction`, `WarnNearLimits`, `ReportContextUsage`, `compact_now`) shares the same `_shared` pair-safe cutoffs.
