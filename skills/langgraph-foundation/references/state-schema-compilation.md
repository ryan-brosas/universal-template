<!-- capsule-v2 -->
# StateGraph compile pipeline — How do typed state schemas become channels, and which graph errors fail at build time?

**Source:** LangGraph MIT `main@f09cfe8ffc1eeffd68f4b628ed69c30f7cad229f`; Codebase Memory `ext-langgraph`. **Question:** How does an `Annotated` field become the right channel, and what validation runs before execution?

## Annotation → channel resolution ladder + validate() source/target closure
**Path/Symbol:** `libs/langgraph/langgraph/graph/state.py:_get_channels` (:1815-1838), `_get_channel` (:1850-1875), `_is_field_channel` (:1876-1903), `_is_field_binop` (:1904-1923), `_is_field_managed_value` (:1925-1943), `validate` (:1129-1176), `add_edge` waiting-edges (:928-981).
**Signature:** `_get_channels(schema) -> (channels: dict[str, BaseChannel], managed: dict[str, ManagedValueSpec], type_hints)`; `compile(checkpointer=None, *, interrupt_before=None, interrupt_after=None, ...)`.
**Data Shape:** Schema = TypedDict/pydantic/dataclass with `__annotations__`; no annotations ⇒ single `__root__` LastValue channel. Reducer annotation = bare 2-positional-param callable → BinaryOperatorAggregate; channel instance/class in metadata wins first; managed values excluded from root schemas.

### Decisive source
```python
def _get_channel(name, annotation, *, allow_managed=True):
    # strip Required/NotRequired wrappers first
    if manager := _is_field_managed_value(name, annotation):
        if allow_managed: return manager
        else: raise ValueError(f"This {annotation} not allowed in this position")
    elif channel := _is_field_channel(annotation):   # Annotated[T, SomeChannel(...)] / class
        channel.key = name; return channel
    elif channel := _is_field_binop(annotation):     # Annotated[T, my_reducer] (2-positional sig)
        channel.key = name; return channel
    fallback: LastValue = LastValue(annotation)      # default: last-write-wins
    fallback.key = name
    return fallback
```
**Flow:** validate() assembles sources from edges+branches+node.ends and targets likewise; unknown endpoints raise; missing START edge raises ("Graph must have an entrypoint"); branch specs without path_map implicitly may target ANY node (affects drawing and target validation). Multi-source `add_edge(["a","b"], "c")` becomes a WAITING edge compiled into NamedBarrierValue semantics. DeltaChannel instances get their typ REBUILT from the annotated origin (unwrapping Required/NotRequired). Duplicate single-source edges raise early — "For multiple edges, use StateGraph with an Annotated state key" pointing at reducers as the merge story.

**Invariant:** Channel key assignment happens at schema resolution (`channel.key = name`) — reusing a channel instance across two keys silently retargets its writes. Reducer detection is SIGNATURE-based (exactly two positional-or-keyword params), not name-based; wrong arity raises with the offending signature echoed.

**Probe:** `grep -n 'def _is_field_channel\|def _is_field_binop' libs/langgraph/langgraph/graph/state.py` → :1876/:1904; `grep -n 'Already found path for node' libs/langgraph/langgraph/graph/state.py`. Direct tests: `tests/test_pregel.py:767` family exercises InvalidUpdateError through compiled StateGraph; `tests/test_state.py` covers schema resolution.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-langgraph", query: "_get_channels", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the annotation-resolution precedence (managed > channel instance > binop reducer > LastValue fallback) for declarative state binding. Adapt typing-introspection mechanics to your host runtime. Omit pydantic v1 shim paths (`_internal/_pydantic.py`) unless you support both pydantic majors.
