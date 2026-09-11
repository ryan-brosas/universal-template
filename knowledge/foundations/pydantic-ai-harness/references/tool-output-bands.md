<!-- capsule-v2 -->
# Tool-output size bands — ordered (over, action) triggers with a `then` fallback so a lossless spill never silently drops

**Source:** pydantic-ai-harness (MIT) `main@c79fabc58fd3bd587dcc27f9e7d9de179d748cf0`; Codebase Memory `pydantic-ai-harness`. **Question:** how does a harness manage oversized tool returns by size band, keeping the full payload retrievable (lossless) and falling back gracefully when an action cannot run?

## Size bands and actions
**Path/Symbol:** `pydantic_ai_harness/tool_output_limits/_bands.py` (85L) — `Band`, `Passthrough`, `Truncate`, `Spill`, `Summarize`, `Action`; `_payload.py` (138L) — `TruncationStrategy`, `strip_ansi`, `is_binary`, `to_bytes`; `_capability.py` (580L); `_store.py` (153L).
**Signature:** `Band(over: int, action: Action)`; `Action = Passthrough | Truncate | Spill | Summarize`; each action carries optional `then: Action | None`.
**Data Shape:** a band is a `(over, action)` pair — when a tool return's measured size is at least `over`, its `action` runs. `ToolOutputLimits` holds an ordered band list and picks the FIRST match (largest threshold that fits), passing through anything below the smallest threshold.

### Decisive source
```python
# Every action carries an optional `then` fallback, applied when the action
# cannot run -- Spill whose store errors, Truncate/Summarize on a binary
# payload, a Summarize whose model call raises.
# Spill(then=Truncate()) is the default: lossless when the store works, a
# bounded truncation otherwise, never a silent drop.
# is_binary: raw byte payloads must NEVER be stringify-truncated.
```

**Flow:** measure return size (chars or tokens) → find first band whose `over` fits → run action → on failure, run `then`. `Spill` persists the full return and replaces it with a `read_tool_result` handle, preview, and shape sketch; `Truncate` clamps stringified return to `max_chars` (always characters, independent of the `over_tokens` size unit); `Summarize` replaces with a size-gated LLM summary (`model=None` inherits the running agent's model).
**Invariant:** never a silent drop — every lossy or failing path has a `then` fallback; binary payloads are never stringify-truncated; token measurement reuses the compaction heuristic `estimate_token_count` so the two capabilities stay aligned.
**Probe:** `tests/tool_output_limits/test_tool_output_limits.py` pins band selection, spill/truncate/summarize behavior, and fallback on store error.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-ai-harness", query: "Band Spill Truncate Summarize ToolOutputLimits", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ordered-band model with mandatory `then` fallbacks and binary safety; adapt the size-measurement unit and store; omit host-specific spill store backends.
