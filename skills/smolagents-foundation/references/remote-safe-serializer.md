<!-- capsule-v2 -->
# SafeSerializer prefix protocol — how do values cross the sandbox boundary without pickle risk by default?

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory `ext-smolagents`. **Question:** What is the exact wire format for `send_variables`/final-answer payloads, which types survive safe mode, and how is the pickle fallback gated at BOTH serialize and deserialize time?

## Tagged JSON with dual-prefix envelope
**Path/Symbol:** `src/smolagents/serialization.py:SafeSerializer` — `to_json_safe` (:75-171), `from_json_safe` (:173-249), `dumps/loads` (:251-346), `get_deserializer_code(allow_pickle)` (:451-514); consumers `remote_executors.py:115-131, 306-332`.
**Signature:** `dumps(obj, allow_pickle=False) -> "safe:{json}" | "pickle:{b64}"`; `loads(data, allow_pickle=False)`; `SAFE_PREFIX="safe:"`; type markers via `{"__type__": ..., "data": ...}` envelopes.
**Data Shape:** Fast-path exact-type checks first (str/int/float/bool/None/list/tuple/dict); extended markers tuple/set/frozenset/bytes(base64)/complex{real,imag}/datetime-family(isoformat)/Decimal(str)/Path(str)/PIL.Image(png-b64)/ndarray{data,dtype}/dataclass{name,module,fields}; dict with non-str keys → `dict_with_complex_keys` pair-list.

### Decisive source
```python
# :313-320 — deserialize-side gate mirrors the serialize side; both must agree:
elif data.startswith("pickle:"):
    if not allow_pickle:
        raise SerializationError(
            "Pickle data rejected: allow_pickle=False requires safe-only data. ...")
    return pickle.loads(base64.b64decode(data[7:]))
else:
    # No prefix - legacy format, assume pickle
    if not allow_pickle:
        raise SerializationError("Pickle data rejected: ...")
```

**Flow:** Host→sandbox (`send_variables`): dumps with the executor's allow_pickle flag → generates a STANDALONE `_deserialize` function from the real source (`get_deserializer_code`) where the pickle branches are literally included or replaced by raises → executes `vars_dict = _deserialize(repr(serialized)); locals().update(vars_dict)`. Sandbox→host (final answer): inline twin serializer produces prefixed string inside FinalAnswerException; host `_deserialize_final_answer` re-parses with the same gate. Optional deps (numpy/PIL) use a class-level cache of import attempts so absence is decided once. Dataclasses deliberately DO NOT reconstruct: decode returns an annotated dict (`__dataclass__`/`__module__` keys) because the class may not exist host-side.
**Invariant:** allow_pickle is enforced independently on BOTH ends and defaults False everywhere; the deserializer codegen means flipping the flag changes generated remote code, not just host behavior — a port that gates only `loads()` still ships pickle-capable code into the sandbox. Unprefixed data is always legacy-pickle and always rejected in safe mode.
**Probe:** `tests/test_serialization.py::TestDefaultBehavior.test_dumps_defaults_to_safe/:test_loads_defaults_to_safe` (:222-249), `TestSafeMode.test_safe_mode_blocks_custom_classes/:test_safe_mode_blocks_pickle_deserialization` (:47-68), `TestGeneratedDeserializerCode` (:887+). Live: roundtrip {tuple,set,datetime,Path,bytes} matrix PASS; `loads("pickle:AAAA", False)` → SerializationError.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-smolagents", query: "SafeSerializer to_json_safe get_deserializer_code pickle prefix", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the marker vocabulary and the two-sided gate plus codegen approach when the far side can't import your package. Adapt the marker set to your domain types. Omit pickle entirely if you never need opaque objects — every consumer here works in safe-only mode.
