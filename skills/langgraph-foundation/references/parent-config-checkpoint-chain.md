<!-- capsule-v2 -->
# Parent-config checkpoint chain — How does a durable runtime reconstruct thread history and fork-safe ancestor walks from checkpoints?

**Source:** LangGraph MIT `main@f09cfe8ffc1eeffd68f4b628ed69c30f7cad229f`; Codebase Memory `langgraph`. **Question:** Time travel, history UIs, and delta-channel replay all need "the checkpoints before this one" — but threads can fork (update_state on an old checkpoint). How is ancestry stored and walked so forks contribute only their own path?

## Store the parent id at put; rebuild a full config at get; walk parent_config, never list(before=)
**Path/Symbol:** `libs/checkpoint/langgraph/checkpoint/base/__init__.py:CheckpointTuple` (:139-146), `BaseCheckpointSaver.get_delta_channel_history` (:582-649); `libs/checkpoint/langgraph/checkpoint/memory/__init__.py:put` (:421-465), `get_tuple` (:230-310); `libs/langgraph/langgraph/pregel/main.py:get_state_history` (:1480-1531).
**Signature:** `CheckpointTuple(config: RunnableConfig, checkpoint: Checkpoint, metadata: CheckpointMetadata, parent_config: RunnableConfig | None = None, pending_writes: list[PendingWrite] | None = None)`; `get_state_history(config, *, filter=None, before=None, limit=None) -> Iterator[StateSnapshot]`.
**Data Shape:** Each saver stores the parent's `checkpoint_id` alongside the checkpoint — the memory saver's `put` stores `(checkpoint_bytes, metadata_bytes, config["configurable"].get("checkpoint_id"))`, i.e. the config's OWN checkpoint_id field IS the parent pointer. `get_tuple` rebuilds `parent_config` as `{"configurable": {"thread_id", "checkpoint_ns", "checkpoint_id": parent_id}}`, or `None` at the root.

### Decisive source
```python
        self.storage[thread_id][checkpoint_ns].update(
            {
                checkpoint["id"]: (
                    self.serde.dumps_typed(c),
                    self.serde.dumps_typed(get_checkpoint_metadata(config, metadata)),
                    config["configurable"].get("checkpoint_id"),  # parent
                )
            }
        )
```
```python
        while cursor_config is not None and remaining:
            tup = self.get_tuple(cursor_config)
            if tup is None:
                break
            if tup.pending_writes:
                for write in reversed(tup.pending_writes):
                    ch = write[1]
                    if ch in remaining:
                        collected_by_ch[ch].append(write)
            for ch in list(remaining):
                if ch in tup.checkpoint["channel_values"]:
                    seed_by_ch[ch] = tup.checkpoint["channel_values"][ch]
                    remaining.discard(ch)
            cursor_config = tup.parent_config
```

**Flow:** `put` records the parent pointer; `get_tuple`/`list` rebuild `parent_config` on every read (nothing extra is stored). `get_state_history` first delegates to the matching subgraph when a recast `checkpoint_ns` is present, then merges `self.config`, coerces `thread_id` to str, EAGERLY consumes `checkpointer.list(...)` into a list ("to avoid holding up the db cursor"), and yields snapshots newest-first with cursor pagination via `before=<snapshot.config>`. The default `get_delta_channel_history` walks `get_tuple` + `parent_config` ONCE for all requested channels (each ancestor visited once, not once per channel), collects each channel's `pending_writes` newest→oldest then reverses to oldest→newest, and terminates per-channel at the nearest ancestor whose `channel_values[ch]` is populated — that value becomes the entry's `seed`; reaching the root without a stored value omits `seed` entirely (consumer treats absence as "start empty"). Savers with direct storage access override for performance, but the return contract is fixed by the default.
**Invariant:** History is a linked list keyed by parent id, not a time series — forked threads share prefixes but diverge, so ancestor queries must follow `parent_config`, never `list(before=...)`; every walk terminates at `parent_config is None`; a missing seed means "start empty", never an error.
**Probe:** `python -m pytest "tests/test_pregel.py::test_invoke_checkpoint_three" -q` — 3 passed / 4 env-blocked ([postgres_pipe]/[postgres_pool] params: no postgres server; memory + sqlite green) — pins limit/before cursor pagination, newest-first ordering, and `get_state(cfg).parent_config == <previous snapshot config>` after `update_state`. `python -m pytest libs/checkpoint-sqlite/tests/test_get_delta_channel_history.py -o addopts="" -q` — 7 passed (default parent-chain walk against real SqliteSaver, incl. seed-omitted-at-root sync+async). One-shot MemorySaver probe: put two checkpoints where the second's config carries the first's id ⇒ `get_tuple(c2).parent_config["configurable"]["checkpoint_id"] == c1 id`, root tuple has `parent_config is None`. Conformance specs read: `libs/checkpoint-conformance/langgraph/checkpoint/conformance/spec/test_put.py::test_put_parent_config` (:209-228) and `test_get_tuple.py::test_get_tuple_parent_config` (:124-149). Byte-exact: `grep -c "cursor_config = tup.parent_config" libs/checkpoint/langgraph/checkpoint/base/__init__.py` → 2 (sync+async twins); `grep -c '"checkpoint_id": parent_checkpoint_id' libs/checkpoint/langgraph/checkpoint/memory/__init__.py` → 3; `grep -c "eagerly consume list() to avoid holding up the db cursor" libs/langgraph/langgraph/pregel/main.py` → 2.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "langgraph", query: "CheckpointTuple parent_config get_state_history get_delta_channel_history parent chain walk", limit: 8 });
```

## Verdict
Adopt store-parent-id-at-put + rebuild-config-at-get (zero extra storage, works for any backend), the eager-list consumption before yielding (never hold a DB cursor across an iterator), and the single-pass multi-channel ancestor walk with per-channel seed termination. Adopt the parent-chain-walk-not-list-before rule for any fork-safe history feature. Adapt cursor pagination (`before`/`limit`) to your storage's native ordering; omit saver-specific fast paths until the generic walk is proven correct against your backend.
