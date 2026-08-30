<!-- capsule-v2 -->
# Session scope key — how do composite identity keys stay collision-free and deterministic?

**Source:** mem0 MIT `main@001c2352`; Codebase Memory `mem0`. **Question:** how is the last-messages session key built from up to three ids without delimiter collisions?

## Connected graph-selected seam
**Path/Symbol:** `mem0/memory/main.py`: `_escape_scope_value` (:407-409), `_build_session_scope` (:412-419); consumed at Phase 0 (:919-920) and Phase 8 (:1193); storage side `SQLiteManager.get_last_messages(session_scope, limit=10)` (storage.py :298).
**Signature:** `_build_session_scope(filters) -> str` — `"user_id=u&agent_id=a&run_id=r"` with only provided parts, keys sorted.
**Data Shape:** percent-encoding of JUST the structural delimiters: `%→%25`, `&→%26`, `=→%3D`; applied to values only, never keys.

### Decisive source
```python
def _escape_scope_value(val):
    """Escape the structural delimiters of the session scope key."""
    return str(val).replace("%", "%25").replace("&", "%26").replace("=", "%3D")

def _build_session_scope(filters):
    parts = []
    for key in sorted(["user_id", "agent_id", "run_id"]):   # deterministic order
        val = filters.get(key)
        if val:
            parts.append(f"{key}={_escape_scope_value(val)}")
    return "&".join(parts)
```

**Flow:** every add encodes the conversation under this key via `save_messages`; the next add reads the last 10 messages for the same scope as extraction context. Escaping `%` FIRST makes the encoding unambiguous; sorting keys makes `(user,agent)` and `(agent,user)` the same session.
**Invariant:** without escaping, `user_id="a=b"` and `user_id="a", agent_id="b"` would collide into one history lane; without sorting, dict order would fragment sessions across runs. The escape order (% first) is load-bearing — reversing it double-encodes.
**Probe:** `tests/memory/test_session_scope.py::test_ids_containing_delimiters_do_not_collide` (:46), `::test_percent_is_escaped_before_other_delimiters` (:84), `::test_add_pipeline_uses_the_escaped_key` (:122).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mem0", query: "_build_session_scope _escape_scope_value save_messages get_last_messages", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the escape-%-first + sorted-parts key builder verbatim — both orderings are proven by test names; adapt the delimiter set if your key grammar differs.
