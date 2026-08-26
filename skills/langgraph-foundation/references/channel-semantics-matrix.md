<!-- capsule-v2 -->
# Channel semantics matrix — Which channel class do I pick so concurrent writers get the right merge behavior?

**Source:** LangGraph MIT `main@f09cfe8ffc1eeffd68f4b628ed69c30f7cad229f`; Codebase Memory `ext-langgraph`. **Question:** What does each channel family do when zero, one, or many updates arrive in a single superstep — and which raise?

## Nine channel classes, three update contracts
**Path/Symbol:** `libs/langgraph/langgraph/channels/last_value.py:LastValue.update` (:52-70), `binop.py:BinaryOperatorAggregate.update` (:123-144), `topic.py:Topic.update` (:61-72), `ephemeral_value.py:EphemeralValue.update` (:46-62), `named_barrier_value.py:NamedBarrierValue.update/consume` (:49-81), `last_value.py:LastValueAfterFinish` (:81-146).
**Signature:** All implement `update(values: Sequence[Update]) -> bool` on the `BaseChannel` protocol (`channels/base.py`: `get/is_available/update/consume/finish/checkpoint/from_checkpoint`).
**Data Shape:** Channels carry `(key, typ)` slots; equality is CLASS + config only (`LastValue.__eq__` returns `isinstance(value, LastValue)` ignoring typ) so schema recompiles dedupe.

### Decisive source
```python
# LastValue.update — at most ONE value per superstep; >1 is a hard error:
if len(values) != 1:
    msg = create_error_message(
        message=f"At key '{self.key}': Can receive only one value per step. Use an Annotated key to handle multiple values.",
        error_code=ErrorCode.INVALID_CONCURRENT_GRAPH_UPDATE,
    )
    raise InvalidUpdateError(msg)
self.value = values[-1]
```
**Flow (per family):**
- **LastValue**: 0 writes → no-op False; exactly 1 → store; >1 → `InvalidUpdateError` (`INVALID_CONCURRENT_GRAPH_UPDATE`). The default for un-annotated state keys.
- **Topic(accumulate=False)**: clears then extends flattened values (list items are flattened via `_flatten`); accumulate=True appends across steps. Empty update after clear reports not-updated.
- **BinaryOperatorAggregate(typ, op)**: first write seeds MISSING value, then folds; an `Overwrite` bypasses the fold entirely; TWO Overwrites in one superstep → `InvalidUpdateError`. `_get_overwrite` recognizes THREE forms: dataclass instance, sentinel dict `{"__overwrite__": v}`, and JSON-erased `{"type": "__overwrite__", "value": v}` (orjson through the API server). `_strip_extras` maps abc Sequence/Set/Missing types to list/set/dict constructors.
- **EphemeralValue(guard=True)**: one value/step enforced like LastValue but with its own message naming `guard=False`; empty sequence CLEARS (returns True if there was a value) — this clearing-on-empty is what makes it ephemeral.
- **NamedBarrierValue(names)**: values must be members of `names` else InvalidUpdateError; available only when `seen == names`; `consume()` resets seen — used by waiting edges (`add_edge(["a","b"], "c")`).
- **LastValueAfterFinish / NamedBarrierValueAfterFinish**: hold writes until `finish()` then expose once; `consume()` clears. Used for END-channel semantics.
- **UntrackedValue**: never persisted to checkpoints (filtered in `put_writes`).

**Invariant:** A channel's `update()` returning True means state changed and the version MUST bump; `apply_writes` only adds updated+available channels to the trigger set. Equality-by-class-and-config lets checkpoints migrate between graph builds.

**Probe:** `grep -n 'Can receive only one value per step' libs/langgraph/langgraph/channels/last_value.py` → 1 hit inside INVALID_CONCURRENT_GRAPH_UPDATE message; `grep -c 'seen_overwrite' libs/langgraph/langgraph/channels/binop.py` → 4; `grep -rn '__overwrite__' libs/langgraph/langgraph/channels/binop.py | wc -l` → 2. Direct tests: `tests/test_channels.py:33 test_last_value`, `:94 test_binop`, `:180 test_delta_channel_overwrite`, `:191 test_overwrite_dataclass_form_survives_json_roundtrip`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-langgraph", query: "BinaryOperatorAggregate update", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the protocol shape (get/is_available/update/consume/finish + checkpoint round-trip) and the per-family concurrency contracts verbatim — they are the port. Adapt type-stripping details to your typing runtime. Omit the JSON-erased Overwrite form if your host never serializes state updates through an HTTP API layer.
