<!-- capsule-v2 -->
# Messages reducer contracts — How do message lists merge, remove, and stay stable across checkpoint replays?

**Source:** LangGraph MIT `main@f09cfe8ffc1eeffd68f4b628ed69c30f7cad229f`; Codebase Memory `ext-langgraph`. **Question:** What are the exact semantics of add_messages upsert/remove, and what does the DeltaChannel batch reducer deliberately NOT do?

## Id-upsert merge with tombstones; REMOVE_ALL truncates; batch reducer trades parity for speed
**Path/Symbol:** `libs/langgraph/langgraph/graph/message.py:add_messages` (:61-241), `_messages_delta_reducer` (:247-302), `REMOVE_ALL_MESSAGES = "__remove_all__"` (:38).
**Signature:** `add_messages(left: Messages, right: Messages, *, format: Literal["langchain-openai"] | None = None) -> Messages`; `_messages_delta_reducer(state: list[AnyMessage], writes: list[list[AnyMessage]]) -> list[AnyMessage]`.
**Data Shape:** Inputs coerced (str/tuple/dict → BaseMessage via convert_to_messages + message_chunk_to_message); missing ids assigned uuid4 on BOTH sides before merging.

### Decisive source
```python
# merge — id collision REPLACES in place; unknown-id RemoveMessage is an ERROR:
merged = left.copy()
merged_by_id = {m.id: i for i, m in enumerate(merged)}
for m in right:
    if (existing_idx := merged_by_id.get(m.id)) is not None:
        if isinstance(m, RemoveMessage):
            ids_to_remove.add(m.id)
        else:
            ids_to_remove.discard(m.id)
            merged[existing_idx] = m
    else:
        if isinstance(m, RemoveMessage):
            raise ValueError(f"Attempting to delete a message with an ID that doesn't exist ('{m.id}')")
        merged.append(m)
...
if remove_all_idx is not None:
    return right[remove_all_idx + 1:]   # everything before the tombstone is dropped
```
**Flow:** append-only by default; same-id write = positional update (streaming chunks finalize this way); RemoveMessage = tombstone; the special id `__remove_all__` truncates history and keeps only what follows it. The batch delta reducer processes ALL writes in ONE pass with a dict index — dedup + tombstone without calling add_messages — and is explicitly NOT full parity: "REMOVE_ALL_MESSAGES, unknown-id RemoveMessage errors, missing-id UUID assignment, and BaseMessageChunk conversion are not handled here." Its fast path skips convert_to_messages when state[0] is already a BaseMessage.

**Invariant:** add_messages must be usable as `Annotated[list, add_messages]`; its determinism given identical (left,right) makes checkpointed message state replay-stable. The batch reducer exists BECAUSE DeltaChannel requires batching-invariance (`reducer(reducer(s,xs),ys) == reducer(s,xs+ys)`); per-write add_messages folds would be quadratic AND non-associative under chunking.

**Probe:** `grep -n 'REMOVE_ALL_MESSAGES' libs/langgraph/langgraph/graph/message.py | head -3` → :33/:38/:209; `grep -n "Attempting to delete a message with an ID" libs/langgraph/langgraph/graph/message.py` → :229. Direct tests: `tests/test_messages_state.py:32/:46/:58` add_messages merge assertions; `tests/test_channels.py:300 test_messages_delta_reducer_coerces_state`, `:314 test_messages_delta_reducer_tuple_write_is_one_message`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-langgraph", query: "_messages_delta_reducer", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt id-upsert/tombstone/REMOVE_ALL grammar for any conversation-state store; adopt the batch-reducer pattern when pairing with delta channels. Adapt coercion breadth to your message type. Omit the langchain-openai format mapper if your host has no OpenAI wire compatibility layer.
