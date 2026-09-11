<!-- capsule-v2 -->
# Stream-mode output projection — Given a finished task's writes, which stream chunks does each mode emit?

**Source:** LangGraph MIT `main@f09cfe8ffc1eeffd68f4b628ed69c30f7cad229f`; Codebase Memory `langgraph`. **Question:** What exact payload does `values`, `updates`, or `tasks` mode produce for a task's writes — and which writes never stream at all?

## Writes are classified by their FIRST tuple, then projected per mode
**Path/Symbol:** `libs/langgraph/langgraph/pregel/_loop.py:PregelLoop.output_writes` (:1416-1466), `libs/langgraph/langgraph/pregel/_io.py:map_output_updates` (:118-174) + `map_output_values` (:100-115), mode union `libs/langgraph/langgraph/types.py:StreamMode` (:122-136).
**Signature:** `output_writes(self, task_id: str, writes: WritesT, *, cached: bool = False) -> None`; `map_output_updates(output_channels, tasks: list[(PregelExecutableTask, writes)], cached=False) -> Iterator[dict]`.
**Data Shape:** Stream queue tuples are `(ns_tuple, mode, payload)`; updates payloads are `{node_name: {chan: val} | val | None}` grouped per task; `writes[0]` is one of INTERRUPT / ERROR / RETURN / channel key.

### Decisive source
```python
# _loop.py output_writes — classification gate:
            if task.config is not None and TAG_HIDDEN in task.config.get(
                "tags", EMPTY_SEQ
            ):
                return
            if writes[0][0] == INTERRUPT:
                # in loop.py we append a bool to the PUSH task paths to indicate
                # whether or not a call was present. If so,
                # we don't emit the interrupt as it'll be emitted by the parent
                if task.path[0] == PUSH and task.path[-1] is True:
                    return
                ...
                if "updates" in stream_modes:
                    self._emit("updates", lambda: iter(interrupts))
                if "values" in stream_modes:
                    current_values = read_channels(self.channels, self.output_keys)
                    # self.output_keys is a sequence, stream chunk contains entire state and interrupts
                    if isinstance(current_values, dict):
                        current_values[INTERRUPT] = interrupts[0][INTERRUPT]
                        self._emit("values", lambda: iter([current_values]))
            elif writes[0][0] != ERROR:
                self._emit("updates", map_output_updates, self.output_keys, [(task, writes)], cached)
```
```python
# _io.py map_output_updates — the anti-merge Counter rule:
            counts = Counter(chan for chan, _ in writes)
            if any(counts[chan] > 1 for chan in output_channels):
                updated.extend((task.name, {chan: value}) for chan, value in writes
                               if chan in output_channels)
            else:
                updated.append((task.name, {chan: value for chan, value in writes
                                            if chan in output_channels}))
```

**Flow:** Task finishes -> `output_writes`: (1) TAG_HIDDEN task -> nothing ever streams; (2) first write INTERRUPT -> nested-PUSH-with-call suppressed (parent level owns it), else `{INTERRUPT: (...)}` dict goes to updates, and values mode either merges it into the full state read (sequence output_keys) or emits interrupts alone (string output_key); (3) first write ERROR -> this hook streams nothing (error surfaces via runner/panic paths); (4) otherwise updates mode projects the task's channel writes filtered to output_keys, with RETURN-channel values keyed by task name; (5) tasks/debug modes additionally emit start/finish events unless `cached=True`. `map_output_values` only fires when pending writes touched an output channel or an interrupt flush forces a read.
**Invariant:** Hidden-tagged tasks never stream; ERROR-first tasks never produce updates chunks from this path; one task writing one channel N>1 times yields N per-write dicts, never a silently-merged value.
**Probe:** `python -m pytest tests/test_pregel.py::test_stream_mode_messages_command -q` (pins combined-mode tuple tagging around interrupts); plus inline: two parallel nodes each writing `{"xs": [n]}` under `stream_mode="updates"` yield exactly two per-task dicts in node order.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "langgraph", name_pattern: "(_output_writes|output_writes|StreamMode)", limit: 10 });
```

## Verdict
Adopt the first-write classification gate and the TAG_HIDDEN suppression as-is — they are what keeps engine bookkeeping out of user streams. Adapt payload shapes and mode names to your host's stream protocol. Omit the v1/v2 wire transformers (`_output_mapper`, test_stream_events_v3*) unless you must evolve a public stream format; they are compatibility shims, not kernel semantics.
