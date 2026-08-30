<!-- capsule-v2 -->
# track invocation stack — how are nested LMP calls linked into parent-child invocation trees across threads?

**Source:** ell MIT `main@9d129846203e75efeb4e5cddd3fb1c164dc0b243`; Codebase Memory `ext-ell`. **Question:** How do I build a who-called-whom DAG of LLM invocations when LMPs invoke other LMPs, possibly on worker threads?

## thread-local stack + random ids
**Path/Symbol:** `src/ell/lmp/_track.py` (`_invocation_stack = threading.local()` :27; `get_current_invocation` :30-33; `push_invocation` :36-39; `pop_invocation` :42-44; core `tracked_func` :62-197).
**Signature:** `tracked_func(*fn_args, _get_invocation_id=False, **fn_kwargs)` — the `_get_invocation_id` flag returns `(result, invocation_id)`.
**Data Shape:** id format `"invocation-" + secrets.token_hex(16)`; stack holds id strings per thread.

### Decisive source
```python
# _track.py:66-77 and 182-187
invocation_id = "invocation-" + secrets.token_hex(16)
...
parent_invocation_id = get_current_invocation()
try:
    push_invocation(invocation_id)
    ...
    if _get_invocation_id:
        return result, invocation_id
    else:
        return result
finally:
    pop_invocation()
```

**Flow:** every tracked call mints a fresh random id BEFORE executing; reads the thread-local top as parent; pushes itself so nested tracked calls (same or different LMP) observe it via `get_current_invocation`; the model-facing wrapper receives it as `_invocation_origin`, which providers embed into every returned `_lstr` — that is how output text inherits traceable lineage. Persistence records the edge as `Invocation.used_by_id = parent_invocation_id` (:306). The no-store early path still generates the id and returns `(res, invocation_id)` when flagged, so evaluations can link labels without persistence. Pop sits in `finally`: failed calls unwind the stack correctly.
**Invariant:** thread-locale is what makes concurrent evaluations safe (each worker thread gets its own stack); the upstream XXX comment warns cache-key/global-binding is NOT thread-safe — porters adding caching must re-read that note. Random (not content-hashed) invocation ids are deliberate: identical inputs are distinct events.
**Probe:** `tests/test_evaluation.py:test_evaluation_run_with_missing_params` (:79-89) consumes the tuple contract (`results[0]().output[0] == "mock_output"` through partial-wrapped results carrying invocation ids).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ell", query: "_track invocation stack", limit: 5, fields: ["signature", "name", "file"] });
// rank-1 pair: push_invocation @ src/ell/lmp/_track.py:36-39, pop_invocation @ :42-44
```

## Verdict
Adopt push-before-execute / pop-in-finally with per-thread stacks. Adapt id minting to your id scheme but keep randomness. Omit the `_get_invocation_id` opt-out only if nothing needs to reference child invocations synchronously — evaluations in this repo depend on it.
