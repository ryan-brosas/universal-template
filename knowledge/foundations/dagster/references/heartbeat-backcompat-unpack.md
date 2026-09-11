<!-- capsule-v2 -->
# Daemon heartbeat back-compat unpacker — how do old heartbeat rows deserialize after the type system changed?

**Source:** Dagster Apache-2.0 `master@4344eb7f4cf588c801c17489228790f002276aca`; Codebase Memory `ext-dagster`. **Question:** What must a deserializer tolerate when reading heartbeats written by older versions (enum daemon types, singular error field)?

## before_unpack migration hook
**Path/Symbol:** `python_modules/dagster/dagster/_daemon/types.py:DaemonHeartbeatSerializer.before_unpack` (lines 11-22).
**Signature:** `def before_unpack(self, context, unpacked_dict) -> dict` — runs before standard field mapping.
**Data Shape:** Two legacy shapes handled: `daemon_type` as a serdes enum value (`{"__enum__": "..."}` dict with `.value["__enum__"]` string); singular `error` field instead of `errors` list.

### Decisive source
```python
def before_unpack(self, context, unpacked_dict):
    # Previously daemon types were enums, now they are strings. If we find a packed enum,
    # just extract the name, which is the string we want.
    if isinstance(unpacked_dict.get("daemon_type"), UnknownSerdesValue):
        unknown = unpacked_dict["daemon_type"]
        unpacked_dict["daemon_type"] = unknown.value["__enum__"].split(".")[-1]
        context.clear_ignored_unknown_values(unknown)
    if unpacked_dict.get("error"):
        unpacked_dict["errors"] = [unpacked_dict["error"]]
        del unpacked_dict["error"]
    return unpacked_dict
```

**Flow:** storage read → raw dict → `before_unpack` normalizes legacy fields → normal NamedTuple construction (`check.float_param(timestamp...)` etc.). The enum name is taken from the LAST dot segment of the `__enum__` string; cleared from the unknown-values list so deserialization isn't polluted. Singular `error` becomes a one-element `errors` sequence.
**Invariant:** Health/liveness reads must NEVER fail because a row predates a schema change — an exception here would make the whole daemon fleet look dead. Normalization happens pre-unpack so downstream code sees exactly one canonical shape.
**Probe:** `python_modules/dagster/dagster_tests/daemon_tests/test_types.py::test_heartbeat_backcompat` (lines 20-30).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dagster", query: "DaemonHeartbeatSerializer before_unpack whitelist_for_serdes", limit: 10 });
```

## Verdict
Adopt pre-unpack normalization for persisted operational state; adapt to your serdes layer; omit once no legacy rows remain.
