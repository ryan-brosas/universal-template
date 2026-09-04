<!-- capsule-v2 -->
# Anthropic replayed-history hardening — what must you fix up before resending a conversation the provider already partially rejected?

**Source:** pydantic-ai Apache-2.0 @ `fde1bbb6aff461769a1d6d2440c33c232bf90f03`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** Which wire-payload repairs does a resended Anthropic conversation need, and how do they interact with prompt caching?

## anthropic-replay-hardening
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/models/anthropic.py:` `_drop_unpaired_native_tool_calls` (:3405–3475), call site (:2191), empty-signature guard (:1935–1939), `_build_extra_body` (:541–562).
**Signature:** `_drop_unpaired_native_tool_calls(anthropic_messages) -> None` (in-place); `_build_extra_body(model_settings) -> object | None`.
**Data Shape:** blocks are typed objects or str-keyed dicts; native calls = `server_tool_use | mcp_tool_use` types; returns = `BetaMCPToolResultBlock` or ANY dict block carrying `tool_use_id`.

### Decisive source
```python
unpaired = (block['type'] in ('server_tool_use', 'mcp_tool_use')
            and block['id'] not in returned_native_tool_call_ids)
tool_search = block.get('name') in ('tool_search_tool_bm25', 'tool_search_tool_regex')
if unpaired and (not suffix_is_tool_result_only or tool_search):
    if (cache_control := block.get('cache_control')) is not None:
        # relocate the boundary onto the nearest preceding cacheable block...
    continue   # drop

# signature guard:
# An empty signature (e.g. from an interrupted stream) is never valid,
# so fall back to tagged text rather than triggering a 400 from the API.
if response_part.provider_name == self.system and response_part.signature:
```

**Flow:** collect every answered call id across ALL messages (returns may sit in later turns) → walk backwards tracking `suffix_is_tool_result_only` (turn is user + only tool_results) → drop unpaired native calls EXCEPT where an in-flight MCP call would be legal (suffix of concurrent client results) or FORCED out (tool_search always dropped — Bedrock rejects that shape even where direct API accepts others) → relocate `cache_control` to nearest preceding cacheable carrier so the cache boundary survives → delete turns left empty (API rejects empty messages).
**Invariant:** five rules:
1. Pair lookup is global-by-id, but LEGALITY of an unpaired call is positional (only a tool-result-only user suffix may carry one) — two different scans must both run.
2. Dropping a block that carried `cache_control` must hand the boundary BACK to the nearest preceding cacheable block; letting it vanish silently caches content the user placed outside the boundary.
3. Tool-search calls are retried rather than preserved in flight because Bedrock 400s the orphan shape even when the direct API tolerates it — provider matrix beats single-provider semantics.
4. Never synthesize a fake result block for a dropped call — that lies to the model ("search ran, found nothing") when the correct recovery is re-searching.
5. Empty ThinkingPart signatures (interrupted streams) fall back to tagged text instead of triggering API 400s; sampling settings (temperature/top_p/top_k) ride `extra_body` since anthropic>=1 removed them from create(), with explicit extra_body entries winning the merge.
**Probe:** `tests/models/anthropic/test_unpaired_native_tool_calls.py` (12 dedicated cases :313–782: boundary relocation ×5, in-flight acceptance, agent-run integration); empty-signature `tests/models/test_anthropic.py:3556`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "_drop_unpaired_native_tool_calls _build_extra_body cache_control Bedrock", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the drop-with-boundary-relocation pattern wherever providers reject partially-answered replays; adapt block-type vocabulary and legality windows; omit the tool-search special case where your provider matrix has no divergent rejection behavior.
