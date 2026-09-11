<!-- capsule-v2 -->
# Artifact registration (POST_TOOL_USE phase 1 of the artifact pipeline)

## Source
pipeshub-ai `main@4a02110d` — `hooks/middleware/builtin/artifact_registration.py` (whole file, 231L).

## Path/Symbol
- `ArtifactStore` Protocol — `async store(content, *, tool_name, result_schema, session_id) -> str` (:30)
- `InMemoryArtifactStore(maxsize=500, ttl_seconds=3600)` (:50) — LRU by insertion-order re-insert + lazy TTL expiry on access
- `shape_artifact_registration(store=None, threshold_tokens=2_000, preview_chars=200, resolve_schema=None)` (:133)

## Signature
POST_TOOL_USE middleware that calls `await next_fn()` FIRST, then inspects `ctx.tool_response`; communicates via `ctx.metadata["artifact_meta"] = ToolMessageMeta(...)` for the executor to carry onto `ToolResult.artifact_meta → ToolMessage.artifact_meta`.

## Data Shape
`ToolMessageMeta(artifact_id, summary≤200 chars, tool_name ("a__b" from path's last two segments), tool_args (from `_result_accum_args` metadata), result_schema (via `resolve_schema(short_name)`), original_token_count, turn_index (from scope.turn))`.

## Decisive source
```python
_EXEMPT_SUFFIXES = frozenset({"/retrieve_artifact_content", "/fetch_full_record"})
_EXEMPT_SEGMENTS = frozenset({"/knowledgegraph/"})
...
except Exception:
    logger.warning("artifact_registration: store.store() failed ... "
                   "tool result stays in context as full content")
    return   # fail-open: registration is an enhancement
```

## Flow
Skips failed responses and exempt paths (retrieval/knowledge-graph tools must not recursively register); stringifies non-str content; token-counts; over threshold → persist full content in store, attach meta. **Current turn keeps full content inline** — compaction to a reference happens later in PRE_MODEL (`shape_artifact_compaction`), which is turn-aware.

## Invariant
Two-phase design: registration (write-side, POST_TOOL_USE) never destroys data; compaction (read-side, PRE_MODEL) decides what leaves context. Store failure degrades to "no artifact" — the pipeline must keep working with plain results.

## Probe
`tests/unit/agent_loop_lib/hooks/middleware/builtin/test_artifact_pipeline.py`: `test_above_threshold_creates_artifact` (:235), `test_metadata_includes_tool_name` (:251), `test_error_response_skipped` (:283), `test_retrieve_artifact_content_exempt_from_registration` (:331), LRU/TTL pins :167/:177; E2E `test_register_compact_then_retrieve` (:770).

## Retrieve
`codebase-memory-mcp cli search_graph --project pipeshub-ai --semantic-query '["shape_artifact_registration","ArtifactStore","ToolMessageMeta"]'`

## Verdict
ADOPT. The Protocol + fail-open registration + executor-carried metadata envelope is the portable seam; the LRU+TTL in-memory store is the reference fallback.
