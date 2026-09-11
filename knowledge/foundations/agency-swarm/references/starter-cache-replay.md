<!-- capsule-v2 -->
# Conversation-starter cache replay — how do canned first messages answer instantly without a model call?

**Source:** agency-swarm MIT `main@4d1c35a6dd5ef038a5d15b39803459ff0b5f5578`; Codebase Memory `ext-agency-swarm`. **Question:** Under which exact preconditions may a first user message be answered from a cached transcript, and how is the cache invalidated so stale replays never ship?

## Fingerprint-gated starter cache with live-capture backfill
**Path/Symbol:** `src/agency_swarm/agent/execution.py:get_response` (:162-249, :348-371) + `src/agency_swarm/agent/core.py:refresh_conversation_starters_cache` (:787-814), `warm_conversation_starters_cache` (:816-857); helpers in `conversation_starters_cache.py`.
**Signature:** `compute_starter_cache_fingerprint(agent, *, runtime_state=None, shared_instructions=None, instructions_override=None, use_instructions_override=False) -> str`; `match_conversation_starter(items, cacheable_starters) -> str | None`; `save_cached_starter(agent_name, starter, segment, metadata, fingerprint)`.
**Data Shape:** cache key = normalized starter text; entry = `{items: [...], metadata: {fingerprint, source}}`; cacheable sources MERGED from `conversation_starters` (only when `cache_conversation_starters=True`) + `quick_replies` + `system_reminders`.

### Decisive source
```python
if (sender_name is None                       # USER-initiated only
    and cacheable_starters
    and is_first_message                      # thread store was empty at run start
    and is_simple_text_message(processed_current_message_items)
    and not additional_instructions           # per-run instructions → bypass cache
    and not has_user_context_override         # per-run context → bypass cache
    and hooks_override is None):              # custom hooks → bypass cache
    cache_fingerprint = compute_starter_cache_fingerprint(...)
    matched_starter = match_conversation_starter(processed_current_message_items, cacheable_starters)
    if matched_starter:
        cached_starter = cache_map.get(normalized)
        if cached_starter is not None and cached_starter.metadata.get("fingerprint") != cache_fingerprint:
            cached_starter = None             # fingerprint mismatch ⇒ treat as cold
...
# After a REAL run that matched a starter but had no cache entry:
segment = extract_starter_segment(new_messages, matched_starter) or new_messages
segment = reorder_cached_items_for_tools(segment, self.agent.name)   # tool calls before outputs
cached = save_cached_starter(..., metadata={"source": "live_run"}, fingerprint=cache_fingerprint)
```

**Flow:** warmup — Agency init schedules a daemon thread (`_schedule_starter_cache_warmup`: no running loop ⇒ `asyncio.run`, else background `threading.Thread`) that connects persistent MCP servers then fires every missing starter through a real run; hit path — replay items get fresh run_trace/parent ids, tool artifacts filtered out of replay, final output parsed against `output_type`, synthetic RunResult carries empty raw_responses; streaming variant replays via `stream_cached_items_events` so clients see normal event cadence.
**Invariant:** (1) ANY per-run personalization (instructions/context/hooks overrides) must bypass the cache or one user's customization leaks into another's replay; (2) the fingerprint binds cached items to agent identity + instructions + tools state — changing any of them invalidates rather than serves stale text; (3) only genuinely FIRST messages qualify (`initial_saved_count == 0`), so caching never hijacks mid-conversation turns; (4) captured segments are reordered tool-call-first because naive transcript order breaks providers requiring call-before-result.
**Probe:** `tests/test_agent_modules/test_conversation_starters_cache.py` (dedicated suite pinning fingerprint/match/replay helpers); streaming side pinned by `tests/test_agent_modules/test_conversation_starters_streaming.py`. Coverage caveat: the execution-loop integration of these helpers has no dedicated end-to-end unit test at HEAD — verified by whole-file read + helper suite.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agency-swarm", query: "conversation starters cache fingerprint replay", limit: 10 });
```

## Verdict
Adopt fingerprint-gated exact-match replay with override-bypass rules; adapt storage location (.agency_swarm dir) to your app's data dir; omit warmup threading if your agents start lazily anyway. Helper suite pins the core; integration loop carries a stated caveat.
