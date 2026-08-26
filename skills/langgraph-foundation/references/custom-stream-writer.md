<!-- capsule-v2 -->
# Custom stream-writer injection — How does mid-step data reach the stream without touching channels or checkpoints?

**Source:** LangGraph MIT `main@f09cfe8ffc1eeffd68f4b628ed69c30f7cad229f`; Codebase Memory `langgraph`. **Question:** Where does the `StreamWriter` callable come from, when is it a no-op, and how do subgraphs inherit it?

## A three-way ladder builds the writer before any node runs
**Path/Symbol:** `libs/langgraph/langgraph/pregel/main.py` custom closure (:2840-2860), `libs/langgraph/langgraph/config.py:get_stream_writer` (:126-196) + `_no_op_stream_writer` (:13-14), `libs/langgraph/langgraph/runtime.py:Runtime.stream_writer` (:107-121), retry guard `libs/langgraph/langgraph/pregel/_retry.py:_TimedAttemptScope._guard_stream_writer` (:260-271, applied :181,:186).
**Signature:** `get_stream_writer() -> StreamWriter` where `StreamWriter = Callable[[Any], None]`; writer ladder inside `Pregel.stream` before `Runtime(...)` construction.
**Data Shape:** Emission = `stream.put((parent_ns_tuple, "custom", c))` onto the SyncQueue; `parent_ns_tuple = get_config()[CONF][CONFIG_KEY_CHECKPOINT_NS].split(NS_SEP)[:-1]` — attribution to the PARENT namespace of the executing task.

### Decisive source
```python
            # set up custom stream mode
            if "custom" in stream_modes:

                def stream_writer(c: Any) -> None:
                    stream.put(
                        (
                            tuple(
                                get_config()[CONF][CONFIG_KEY_CHECKPOINT_NS].split(
                                    NS_SEP
                                )[:-1]
                            ),
                            "custom",
                            c,
                        )
                    )
            elif CONFIG_KEY_STREAM in config[CONF]:
                stream_writer = config[CONF][CONFIG_KEY_RUNTIME].stream_writer
            else:

                def stream_writer(c: Any) -> None:
                    pass
```

**Flow:** (1) top-level run requests `custom` mode -> closure writer that reads the CURRENT config contextvar at call time, so each task attributes emissions to its own parent ns; (2) subgraph entry whose config carries CONFIG_KEY_STREAM but did not re-request custom -> inherits the parent runtime's writer via `Runtime.merge`; (3) anything else -> no-op writer, so nodes can unconditionally call `writer(x)` (it is always injected). `get_stream_writer()` fetches it lazily off the contextvar-backed Runtime; on Python <3.11 async contextvar propagation breaks this (documented limitation). During timed attempts `_guard_stream_writer` wraps the runtime writer so emissions count toward the idle-timeout guard.
**Invariant:** Custom emissions bypass channels entirely: they are never checkpointed, never replayed on resume, and never visible to triggers — resuming after an interrupt does NOT re-deliver pre-interrupt custom chunks. Writers must stay side-effect-safe to call twice because node bodies may re-execute on resume.
**Probe:** `python -m pytest tests/test_pregel.py::test_get_stream_writer -q` (custom-only emission `["custom!"]`, values-mode unaffected, mixed modes tag `("custom", ...)`) ; `grep -cn "_guard_stream_writer" libs/langgraph/langgraph/pregel/_retry.py` → 3.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "langgraph", query: "get_stream_writer custom stream mode writer", limit: 8 });
```

## Verdict
Adopt the inject-always/no-op-default pattern — user code should never branch on streaming availability. Adapt ns-attribution to your host's namespace scheme. Omit the Python <3.11 workaround surface; document the limitation instead.