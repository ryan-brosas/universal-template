<!-- capsule-v2 -->
# state cache key — what identity makes one LMP invocation cache-equivalent to another?

**Source:** ell MIT `main@9d129846203e75efeb4e5cddd3fb1c164dc0b243`; Codebase Memory `ext-ell`. **Question:** When a prompt program is deterministic given its inputs and captured globals, how do I key a result cache so identical calls replay stored outputs instead of re-billing the model?

## sha256 over serialized params + immutable closure state
**Path/Symbol:** `src/ell/util/serialization.py:compute_state_cache_key` (:92-96), `get_immutable_vars` (:70-89), `prepare_invocation_params` (:107-128); consumption in `_track.py` (:95-131 cache branch, :163-166 post-call fallback).
**Signature:** `compute_state_cache_key(ipstr: str, fn_closure: Tuple) -> sha256hex`; `prepare_invocation_params(params: dict) -> (cleaned_params, ipstr, consumes: list)`.
**Data Shape:** `ipstr` = canonical JSON of the serialized kwargs (sort_keys, ensure_ascii=False, repr-default); closure halves are JSON of globals/freevars filtered through the immutability funnel.

### Decisive source
```python
# serialization.py:92-95
def compute_state_cache_key(ipstr, fn_closure):
    _global_free_vars_str = f"{json.dumps(get_immutable_vars(fn_closure[2]), sort_keys=True, default=repr, ensure_ascii=False)}"
    _free_vars_str = f"{json.dumps(get_immutable_vars(fn_closure[3]), sort_keys=True, default=repr, ensure_ascii=False)}"
    state_cache_key = hashlib.sha256(f"{ipstr}{_global_free_vars_str}{_free_vars_str}".encode('utf-8')).hexdigest()
    return state_cache_key
```

```python
# serialization.py:84-85 — mutables collapse to inert markers inside the key
elif isinstance(obj, np.ndarray):
    return obj.tolist()
else:
    return f"<Object of type {type(obj).__name__}>"
```

**Flow:** when the wrapper carries `__ell_use_cache__`, the key is computed pre-call (`ipstr` from `prepare_invocation_params`, which ALSO extracts `consumes` — the origin-trace ids embedded in params via regex over the serialized JSON) and `get_cached_invocations(lmp_id, state_cache_key)` runs; hits deserialize stored results and return early. Misses fall through to execution and compute the key post-call only if not already computed. The immutability funnel makes the key honest: primitives/lists/dicts recurse, sets/frozensets sort for determinism, ndarrays become lists, and ANY other object type degrades to a type-name placeholder — so two calls with "equal-looking" mutable objects DO collide (documented upstream hazard), while changed immutable state changes the key.
**Invariant:** cache identity spans THREE planes — argument values, global vars, free vars — because prompts close over all three; omitting the closure halves would replay stale outputs after someone edits a constant the prompt interpolates.
**Probe:** `tests/test_closure.py:test_is_immutable_variable` (:63-64 parametrized: 42/string/tuple True; list/dict False) pins the funnel's classification that feeds this key.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ell", query: "state cache key", limit: 5, fields: ["signature", "name", "file"] });
// rank-1: ext-ell.src.ell.util.serialization.compute_state_cache_key @ src/ell/util/serialization.py:92-96
```

## Verdict
Adopt three-plane keying with an explicit mutability funnel. Adapt serialization to your canonical-JSON rules (sorting is non-negotiable). Omit regex-based consumes extraction if your provenance rides structured fields instead of stringified frozensets.
