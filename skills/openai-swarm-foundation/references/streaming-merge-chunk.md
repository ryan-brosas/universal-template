<!-- capsule-v2 -->
# streaming merge — How are SSE deltas reassembled into one message with parallel tool calls intact?

**Source:** OpenAI Swarm MIT `main@6af0b4caf37dca4526dfd98e9fbd8ce36e7eeb22`; Codebase Memory `ext-openai-swarm`. **Question:** What accumulation structure rebuilds streamed assistant messages — including N parallel tool_calls keyed by index — without losing shards?

## Recursive string-append merge over an index-keyed dict
**Path/Symbol:** `swarm/util.py:merge_chunk` (21-28) + `swarm/util.py:merge_fields` (13-18).
**Signature:** `merge_chunk(final_response: dict, delta: dict) -> None`.
**Data Shape:** `final_response` starts as the seed message in `run_and_stream` (content "", sender, defaultdict of tool_call dicts); each delta is a JSON-ified `ChoiceDelta`.

### Decisive source
```python
def merge_fields(target, source):
    for key, value in source.items():
        if isinstance(value, str):
            target[key] += value
        elif value is not None and isinstance(value, dict):
            merge_fields(target[key], value)

def merge_chunk(final_response: dict, delta: dict) -> None:
    delta.pop("role", None)
    merge_fields(final_response, delta)
    tool_calls = delta.get("tool_calls")
    if tool_calls and len(tool_calls) > 0:
        index = tool_calls[0].pop("index")
        merge_fields(final_response["tool_calls"][index], tool_calls[0])
```

**Flow:** strip `role` → recursive merge (strings CONCATENATE, dicts recurse, None skipped) → if the delta carries tool calls: pop its `index` and merge that shard into `final_response["tool_calls"][index]`.
**Invariant:** Tool-call identity across chunks is the numeric `index`, NOT the call id — the id arrives shard-split too and concatenates like any string field. Only ONE tool call per delta is merged (`tool_calls[0]`) — fine because OpenAI emits one per chunk. `run_and_stream` seeds `final_response["tool_calls"]` as a defaultdict so index access creates slots; it is converted to a list (or None) AFTER streaming ends.
**Probe:** `tests/` has NO unit test for merge_chunk — behavior is exercised only indirectly via REPL usage; porters must pin it with their own round-trip test (state this caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-openai-swarm", query: "merge_chunk stream delta", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt index-keyed shard reassembly + concatenate-on-string as the canonical minimal SSE accumulator (~16 lines). Adapt for providers that batch multiple tool calls per chunk or emit non-dict deltas. Omit nothing if you keep OpenAI chunk shapes; otherwise map your provider's delta grammar onto this one first.
