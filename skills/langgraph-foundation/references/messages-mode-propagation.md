<!-- capsule-v2 -->
# Messages-mode propagation — How do nested LLM tokens reach stream_mode="messages" with dedup and namespace attribution?

**Source:** LangGraph MIT `main@f09cfe8ffc1eeffd68f4b628ed69c30f7cad229f`; Codebase Memory `langgraph`. **Question:** A node may call an LLM anywhere in its body, inside subgraphs, inside tools — how does one handler installed at stream start see every token, attribute it to the right namespace, and emit each message exactly once?

## An inheritable callback handler with per-run metadata and id-based dedup
**Path/Symbol:** `libs/langgraph/langgraph/pregel/_messages.py:StreamMessagesHandler` (:49-256); install site `libs/langgraph/langgraph/pregel/main.py` (:2773-2827).
**Signature:** `StreamMessagesHandler(stream: Callable[[StreamChunk], None], subgraphs: bool, *, parent_ns: tuple[str, ...] | None)`; emits `(ns_tuple, "messages", (message, metadata))` via the stream queue — the same queue as every other stream mode (see `stream-mode-projection`).
**Data Shape:** `self.metadata: dict[UUID, Meta]` maps run_id → `(ns, metadata)`; `self.seen: set[int | str]` holds emitted/known message ids; `Meta = tuple[tuple[str, ...], dict[str, Any]]`.

### Decisive source
```python
class StreamMessagesHandler(BaseCallbackHandler, _StreamingCallbackHandler):
    run_inline = True  # main thread to avoid order/locking issues

    def _emit(self, meta: Meta, message: BaseMessage, *, dedupe: bool = False) -> None:
        if dedupe and message.id in self.seen:
            return
        else:
            if message.id is None:
                message.id = str(uuid4())
            self.seen.add(message.id)
            self.stream((meta[0], "messages", (message, meta[1])))

    def on_chat_model_start(self, serialized, messages, *, run_id, ...):
        if metadata and (not tags or (TAG_NOSTREAM not in tags)):
            ns = tuple(metadata["langgraph_checkpoint_ns"].split(NS_SEP))[:-1]
            if not self.subgraphs and len(ns) > 0 and ns != self.parent_ns:
                return
            ...
            self.metadata[run_id] = (ns, metadata)

    def on_llm_new_token(self, token, *, chunk=None, run_id, ...):
        if not isinstance(chunk, ChatGenerationChunk):
            return
        if meta := self.metadata.get(run_id):
            self._emit(meta, chunk.message)          # chunks: no dedup

    def on_llm_end(self, response, *, run_id, ...):
        if meta := self.metadata.get(run_id):
            if response.generations and response.generations[0]:
                gen = response.generations[0][0]
                if isinstance(gen, ChatGeneration):
                    self._emit(meta, gen.message, dedupe=True)  # final: deduped
        self.metadata.pop(run_id, None)
```

**Flow:** At stream start, if `"messages" in stream_modes`, the graph appends the handler to `run_manager.inheritable_handlers` (`main.py:2821-2827`) with `stream.put` as emitter and `parent_ns` = its own checkpoint_ns split on NS_SEP. Inheritable means every nested runnable — LLM calls in node bodies, subgraphs, tools — receives it automatically; no per-node wiring. Each LLM run registers at `on_chat_model_start`: ns is the PARENT of the executing task (`checkpoint_ns.split(NS_SEP)[:-1]`), and runs deeper than parent_ns are dropped unless `subgraphs=True`. Tokens stream via `on_llm_new_token` (no dedup — each chunk is new); the final message emits at `on_llm_end` with `dedupe=True`, so a non-streaming model emits exactly once while a streaming model's final duplicate is suppressed by id. Node-level outputs are covered separately: `on_chain_start` pre-registers input message ids into `seen` (echoed inputs never emit) and `on_chain_end` scans the node output (dict/BaseModel/dataclass values, sequences, and `Command.update`) for BaseMessage instances. `on_llm_error`/`on_chain_error` just drop the run's metadata. The v1/v2 boundary: a v1 stream strips inherited V2 handlers first (`main.py:2773-2789`) so content-block events cannot leak into the v1 wire protocol, while v1 handlers stay so an outer `subgraphs=True` stream still observes inner streams.
**Invariant:** Exactly-once-per-message-id across the whole run: streaming chunks + final + node outputs all funnel through one `seen` set; inputs are pre-seeded so state echoes never re-emit. Namespace attribution is always the PARENT ns of the emitting run, matching how custom-writer chunks are attributed (see `custom-stream-writer`).
**Probe:** `python -m pytest "tests/test_pregel.py::test_stream_messages_dedupe_inputs" "tests/test_pregel.py::test_stream_messages_dedupe_state" -q` — both pass (input echo suppressed; state-carried message emitted once across two invocations on the same thread). Byte-exact: `grep -c 'run_inline = True' libs/langgraph/langgraph/pregel/_messages.py` → 1; `grep -c 'self.stream((meta\[0\], "messages", (message, meta\[1\])))' libs/langgraph/langgraph/pregel/_messages.py` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "langgraph", query: "StreamMessagesHandler", limit: 8 });
```

## Verdict
Adopt the inheritable-handler + per-run-metadata + global-seen-set shape for any "stream every model token from anywhere in the tree" requirement — it needs zero per-node cooperation and survives arbitrary nesting. Adapt the ns derivation to your host's task-namespace scheme and keep the parent-of-emitter rule so consumers can group chunks by owning node. Omit the v1/v2 dual-protocol machinery unless you must evolve the wire format without breaking old clients.
