<!-- capsule-v2 -->
# Filter call stack — onion composition with first-added-outermost ordering

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** How must middleware-style filters be stored and folded so that the first filter added runs first before `await next(...)` and last after it?

## Filter registration + call-stack fold
**Path/Symbol:** `python/semantic_kernel/filters/kernel_filters_extension.py:KernelFilterExtension.add_filter` (lines 37–58) and `.construct_call_stack` (lines 108–118).
**Signature:** `def add_filter(self, filter_type: ALLOWED_FILTERS_LITERAL | FilterTypes, filter: CALLABLE_FILTER_TYPE) -> None` / `def construct_call_stack(self, filter_type: FilterTypes, inner_function: Callable[[FILTER_CONTEXT_TYPE], Coroutine[Any, Any, None]]) -> Callable[[FILTER_CONTEXT_TYPE], Coroutine[Any, Any, None]]`.
**Data Shape:** Each filter list is `list[tuple[int, CALLABLE_FILTER_TYPE]]` keyed by `id(filter)` (for O(1) removal by identity); three fixed lists (`function_invocation_filters`, `prompt_rendering_filters`, `auto_function_invocation_filters`) selected via `FILTER_MAPPING`. A filter is `Callable[[ctx, next], Awaitable[None]]`.

### Decisive source
```python
def add_filter(self, filter_type, filter):
    ...
    getattr(self, FILTER_MAPPING[filter_type.value]).insert(0, (id(filter), filter))
...
def construct_call_stack(self, filter_type, inner_function):
    stack: list[Any] = [inner_function]
    for _, filter in getattr(self, FILTER_MAPPING[filter_type]):
        filter_with_next = partial(filter, next=stack[0])
        stack.insert(0, filter_with_next)
    return stack[0]
```

**Flow:** add_filter inserts each new filter at index 0 → list reads `[last_added, ..., first_added]`. construct_call_stack starts from `[inner_function]`, iterates the list head-to-tail binding `next=stack[0]`, so the first-added filter ends outermost. Execution: pre-`next` code runs in insertion order; code after `await next(context)` runs in exact reverse; the inner function runs once in the middle.
**Invariant:** First-added filter wraps all later filters — reversing to "iterate and append" or inserting at the end of the list silently flips post-`next` semantics and breaks removal-by-identity.
**Probe:** `python/tests/unit/functions/test_kernel_function_from_method.py::test_function_invocation_multiple_filters` (lines 370–403) pins the exact observable order `["custom_filter1_pre", "custom_filter2_pre", "func", "custom_filter2_post", "custom_filter1_post"]`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "construct_call_stack filter", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the `(id, fn)` tuple list + insert(0) + fold-over-inner construction verbatim for any host with async middleware. Adapt the three hardcoded filter types to your domain's seam set if needed. Omit pydantic modeling of the extension class (`KernelBaseModel`) unless you already have a pydantic settings plane. Streaming caveat: a filter may replace `context.result.value` with its own generator wrapper (see streaming test at lines 406–448), so ports must allow filters to transform streams, not just values.
