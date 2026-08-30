<!-- capsule-v2 -->
# Hook dispatch contract — how do response hooks chain, and what may they return?

**Source:** psf/requests Apache-2.0 `main@8f8b212de8c2129d7954c6cd373762880375620a`; Codebase Memory `ext-requests`. **Question:** What is the exact dispatch semantics of hooks.dispatch_hook including return-value chaining?

## hooks module + registration surface
**Path/Symbol:** `src/requests/hooks.py:dispatch_hook` (:32-48), `default_hooks` (:25-26); registration `models.py:RequestHooksMixin.register_hook` (:257-271); invocation `sessions.py:Session.send` (:791).
**Signature:** `dispatch_hook(key, hooks, hook_data, **kwargs) -> Response`.

### Decisive source
```python
HOOKS = ["response"]                       # only event name that exists

def default_hooks():
    return {event: [] for event in HOOKS}  # ALWAYS list-valued, even when empty

def dispatch_hook(key, hooks, hook_data, **kwargs):
    hook_list = (hooks or {}).get(key)
    if hook_list:
        if isinstance(hook_list, Callable):
            hook_list = [hook_list]        # tolerate single callable instead of list
        for hook in hook_list:
            _hook_data = hook(hook_data, **kwargs)
            if _hook_data is not None:
                hook_data = _hook_data     # None = pass-through unchanged
    return hook_data

# register_hook rejects unknown events loudly:
if event not in self.hooks:
    raise ValueError(f'Unsupported event specified, with event name "{event}"')
```

**Flow:** Session.send calls `dispatch_hook("response", request.hooks, r, **kwargs)` immediately after adapter.send → each registered callable receives the current Response plus send kwargs → a truthy RETURN REPLACES the response flowing into subsequent hooks; returning None keeps prior state → final value becomes THE response (before cookie extraction/redirects).
**Invariant:** Hooks run BEFORE cookies persist and BEFORE redirect resolution — a hook rewriting `location` or `status_code` changes downstream behavior (this ordering is a documented integration seam used by HTTPDigestAuth's own handle_401 hook). Single-callable tolerance means both `hooks={"response": fn}` and `{"response": [fn]}` work; empty-list sentinel interacts with session merge via merge_hooks (`[]` explicitly suppresses session hooks).
**Probe:** Direct tests: `tests/test_requests.py::test_hook_receives_request_arguments` (:1190), `::test_session_hooks_are_used_with_no_request_hooks` (:1200), `::test_session_hooks_are_overridden_by_request_hooks` (:1211), `::test_prepared_request_hook` (:1225); unit level `tests/test_hooks.py::test_hooks`/`::test_default_hooks`. `grep -n "isinstance(hook_list, Callable)" src/requests/hooks.py` → 1 hit (:42).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-requests", query: "dispatch_hook hook_data response", limit: 10 });
```

## Verdict
Adopt list-normalization + None-pass-through chaining. Adapt event names if host needs more than "response" but keep loud unknown-event rejection. Omit nothing.
