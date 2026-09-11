<!-- capsule-v2 -->
# Argument enrichment type preservation — how template call sites pass raw ints/lists/dicts, and where the positional slot lands

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** Do arguments passed from a prompt to an in-template function keep their Python types, or is everything flattened to strings?

## Two read paths per block: render() stringifies, get_value() preserves
**Path/Symbol:** `python/semantic_kernel/template_engine/blocks/code_block.py:CodeBlock._enrich_function_arguments` (139–173); `python/semantic_kernel/template_engine/blocks/var_block.py:VarBlock.render` (68–84) vs `.get_value` (86–99).
**Signature:** `def _enrich_function_arguments(self, kernel, arguments, function_metadata) -> "KernelArguments"`.
**Data Shape:** VarBlock carries `name`; NamedArgBlock carries `name` plus exactly one of `value: ValBlock | None` / `variable: VarBlock | None`.

### Decisive source
```python
if isinstance(token, VarBlock):
    rendered_value = token.get_value(arguments)          # RAW object, no str()
elif isinstance(token, NamedArgBlock):
    if token.variable:
        rendered_value = token.variable.get_value(arguments)  # raw via inner var
    else:
        rendered_value = token.render(kernel, arguments)      # quoted literal → str
else:
    rendered_value = token.render(kernel, arguments)

if not isinstance(token, NamedArgBlock) and index == 1:
    arguments[function_metadata.parameters[0].name] = rendered_value   # positional slot
    continue
arguments[token.name] = rendered_value
```

**Flow:** For each argument token (index 1+): variable-sourced values bypass rendering entirely so `int`, `list`, `dict` arrive intact; quoted literals are strings by construction. A non-named-arg token in slot 1 binds positionally to the callee's FIRST declared parameter name from metadata; named args bind by their own name. Calling a zero-parameter function WITH any argument raises CodeBlockRenderException before invoke.
**Invariant:** The same `$var` block has two distinct read paths — `render()` returns `str(value)` or `""` with a warning when missing (for prompt text), while `get_value()` returns the raw object or None (for call arguments). Conflating them either corrupts typed payloads or leaks un-stringified values into prompts. Missing variables in the positional slot inject None rather than omitting.
**Probe:** `python/tests/unit/template_engine/blocks/test_code_block.py::TestNonStringArguments` (488–581): int/list/dict via named arg AND int via `test_named_arg_with_non_string_type` (560–581, positional `'hello'` + named `count=$repetitions`) all assert `isinstance` preservation; `python/tests/unit/template_engine/blocks/test_var_block.py` pins the render-side warning/"" behavior.
**Coverage caveat:** cited paths checked via check_index_coverage — clean.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "enrich function arguments raw value variable block preserve type", limit: 8, fields: ["signature", "lines"] });
```
(Executed this pass: `_enrich_function_arguments` ranked first, .NET twin second.)

## Verdict
Adopt the dual read path (stringify-for-prompt vs raw-for-call) and metadata-driven positional binding. Adapt the zero-arg-raises rule only with care — it protects against silently ignored template args. Omit the positional-slot convenience if your host grammar requires explicit naming everywhere; SK keeps it because slot-1 is validated at parse time.
