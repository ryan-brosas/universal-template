<!-- capsule-v2 -->
# Budget reduction + offload (cheap-first payload caps)

## Source
pipeshub-ai `main@4a02110d` — `hooks/middleware/builtin/{budget_reduction,offload}.py` (both read whole).

## Path/Symbol
- `shape_budget_reduction(max_result_chars=64_000)` (budget_reduction.py :10) — `_MARKER = "\n[…truncated"`, `_OWN_SUFFIX = "by budget_reduction]"` (:6–7)
- `OffloadStore` Protocol (`write(content) -> handle`) + `InMemoryOffloadStore` (offload.py :11/:22)
- `shape_offload(store=None, threshold_tokens=2_000, preview_lines=10)` (:39)

## Signature
Both are PRE_MODEL reducers. budget_reduction runs unconditionally (Layer 1); offload replaces TOOL bodies over `threshold_tokens` with `[offloaded full result to <path> — first N lines below]` + preview.

## Data Shape
Truncation suffix embeds the omitted char count: `content[:max_result_chars] + f"{_MARKER} {omitted} chars {_OWN_SUFFIX}"`.

## Decisive source
```python
# Skip only messages already truncated by THIS shaper (avoid double-truncation
# on re-runs). Foreign truncation markers do NOT grant a pass — those messages
# can still be far over max_result_chars.
if _OWN_SUFFIX in msg.content:
    shaped.append(msg); continue
```

## Invariant
**Own-marker idempotence**: only this shaper's exact suffix grants a re-run pass; foreign markers don't. Artifact-bearing messages ARE truncated like any other here — the artifact store already holds full content, and L2 replaces them with compact references on later turns. OffloadStore is intentionally minimal (write-only Protocol) so the context engine never depends on the workspace phase; the in-memory default is process-local and NOT durable.

## Probe
`tests/unit/agent_loop_lib/hooks/middleware/builtin/test_artifact_pipeline.py::TestBudgetReductionArtifactHandling`: `test_artifact_messages_truncated_like_others` (:593), `test_small_artifact_messages_untouched` (:610), `test_non_artifact_messages_truncated` (:626).

## Retrieve
`codebase-memory-mcp cli search_graph --project pipeshub-ai --semantic-query '["shape_budget_reduction","shape_offload","OffloadStore"]'`

## Verdict
ADOPT as one capsule: they are the pipeline's two cheapest payload policies (hard per-message char cap; store-and-preview offload) and share the marker-discipline design rule.
