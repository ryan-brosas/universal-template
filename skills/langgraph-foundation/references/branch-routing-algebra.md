<!-- capsule-v2 -->
# Branch routing algebra — How does a conditional edge evaluate, and what can its destinations be?

**Source:** LangGraph MIT `main@f09cfe8ffc1eeffd68f4b628ed69c30f7cad229f`; Codebase Memory `langgraph`. **Question:** What state does a router function see, what may it return, and which destination errors fail fast?

## Routers run as source-node writers over FRESH schema-coerced reads
**Path/Symbol:** `libs/langgraph/langgraph/graph/_branch.py:BranchSpec` (:83-225; `from_path` :88-120, `_route/_aroute` :146-190, `_finish` :192-225), wiring `libs/langgraph/langgraph/graph/state.py:attach_branch` (:1577-1624) + `add_conditional_edges` (:982-1030).
**Signature:** `BranchSpec.from_path(path, path_map: dict | list[str] | None, infer_schema=False)`; `run(writer, reader) -> RunnableCallable`; `_finish(writer, input, result, config) -> Runnable | Any`.
**Data Shape:** `ends: dict[Hashable, str] | None`; a `list` path_map becomes an identity dict; with no path_map the router fn's `Literal[...]` RETURN hint is mined for ends. Writer callable: `(packets: Sequence[str | Send], static: bool) -> Sequence[ChannelWriteEntry | Send]`.

### Decisive source
```python
    def _finish(
        self, writer, input, result, config,
    ) -> Runnable | Any:
        if not isinstance(result, (list, tuple)):
            result = [result]
        if self.ends:
            destinations: Sequence[Send | str] = [
                r if isinstance(r, Send) else self.ends[r] for r in result
            ]
        else:
            destinations = cast(Sequence[Send | str], result)
        if any(dest is None or dest == START for dest in destinations):
            raise ValueError("Branch did not return a valid destination")
        if any(p.node == END for p in destinations if isinstance(p, Send)):
            raise InvalidUpdateError("Cannot send a packet to the END node")
        entries = writer(destinations, False)
        if not entries:
            return input                      # pure passthrough — node output unchanged
        ...
            if need_passthrough:
                return ChannelWrite(entries)  # write WITH the node output as value
            else:
                ChannelWrite.do_write(config, entries)
                return input
```
```python
# attach_branch.get_writes — static declaration keeps END, runtime results drop it:
                    ChannelWriteEntry(
                        p if p == END else _CHANNEL_BRANCH_TO.format(p), None
                    )
                    ...
                if (True if static else p != END)
```

**Flow:** Compile time: `add_conditional_edges` coerces the router to a Runnable, rejects duplicate branch names per source, stores `BranchSpec.from_path(..., infer_schema=True)`. Attach time: reader = `ChannelRead.do_read(select=node-input channels or branch input_schema, fresh=True, mapper=state-coercer)`; the routed writer is appended to the SOURCE node's writers. Runtime: after the node body, `_route` reads fresh channel values and, when both sides are plain dicts AND no explicit branch input_schema was declared, merges the node's own output under them (`{**input, **value}`) so routers see what the node just wrote; result -> list -> map through ends (Send passes through untouched); validations raise; empty destinations passthrough; otherwise writes land on synthetic `branch:to:<dest>` trigger channels.
**Invariant:** Static declarations include END but runtime routes must never emit it (`p != END` filter); None/START destinations are ValueError; `Send(END)` is InvalidUpdateError; unknown end keys raise KeyError from `self.ends[r]` — routers are total functions over their declared ends.
**Probe:** `python -m pytest tests/test_state.py::test_input_schema_conditional_edge -q` (router first-param annotation becomes an isolated read schema); `grep -n "Branch did not return a valid destination" libs/langgraph/langgraph/graph/_branch.py` → exactly :208.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "langgraph", query: "BranchSpec route conditional edge attach_branch", limit: 10 });
```

## Verdict
Adopt routers-as-writers: routing belongs to the source task's execution, costs zero extra tasks, and keeps the trigger algebra unchanged. Adapt the fresh-read merge rule if your host forbids same-step visibility; keep the fail-fast destination validation verbatim. Omit Literal-return-type inference only if your host lacks reflection — then require explicit path_map.