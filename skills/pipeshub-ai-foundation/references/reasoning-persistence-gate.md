<!-- capsule-v2 -->
# Reasoning persistence gate — why is chain-of-thought storage opt-OUT, truncated, and additive at the payload boundary?

**Source:** pipeshub-ai Apache-2.0 @ `main` (pin `6850972`); Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** reasoning transcripts are long and provider-specific — what gets persisted to Mongo vs streamed live, and how does the flag interact with both shapes?

## Env opt-out + 4k truncation over two payload shapes
**Path/Symbol:** `backend/python/app/agents/agent_loop/reasoning_persistence.py:26-61` (`reasoning_persistence_enabled`, `build_reasoning_payload`, `filter_reasoning_parts`).
**Signature:** `build_reasoning_payload(reasoning_turns: list[dict]) -> list[dict] | None`; `filter_reasoning_parts(parts: list[MessagePart]) -> list[MessagePart]`; `_MAX_REASONING_CHARS = 4000`.
**Data Shape:** turns `{turnIndex, content}`; MessagePart dicts with `type=="reasoning"` or `type=="sub_agent"` (recursive `parts`).

### Decisive source
```python
# Chain-of-thought can be long and provider-specific, so persistence is
# opt-OUT via an env var (default on, per product decision ...):
# even when on, per-turn content is truncated before it reaches
# completion_data["reasoning"]/completion_data["parts"] ...
# Live streaming of REASONING_MESSAGE_* events to the frontend is
# UNAFFECTED by this flag — it only gates what gets written to durable storage.
def build_reasoning_payload(reasoning_turns):
    if not reasoning_turns or not reasoning_persistence_enabled():
        return None
    return [
        {**turn, "content": str(turn.get("content", ""))[:_MAX_REASONING_CHARS]}
        for turn in reasoning_turns
    ]
```

**Flow:** streamer accumulates `REASONING_MESSAGE_*` deltas into per-turn entries regardless of the flag → at completion, respond.py asks build_reasoning_payload (turn-list shape) and filter_reasoning_parts (parts-transcript shape, recursing into sub_agent nesting) right before setting completion_data.
**Invariant:** None means "omit the field entirely" — an ADDITIVE field whose absence is indistinguishable from older clients. The flag NEVER touches live streaming, only durable writes. Truncation applies identically in both shapes so no path can bypass the cap.

### Direct test
**Probe:** consumed via respond-pipeline suite: `grep -rn 'build_reasoning_payload\|filter_reasoning_parts' tests/unit/agents/adapter/test_respond_pipeline.py` → assertions pin omission/truncation behavior through the pipeline. Execute from repo root `backend/python`: `grep -c '_MAX_REASONING_CHARS' app/agents/agent_loop/reasoning_persistence.py` → 4.
Coverage caveat recorded honestly: no dedicated unit file for this module; behavior is pinned indirectly by test_respond_pipeline.py.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "reasoning_persistence_enabled build_reasoning_payload filter_reasoning_parts", limit: 3, fields: ["signature", "name", "file"] });
// resolves reasoning_persistence.py Functions line-exact
```

## Verdict
Adopt dual-shape gating with additive-field semantics (None omits), uniform truncation, and strict live-stream/durable-store separation. Adapt env name and cap. Omit Mongo message-document specifics.
