<!-- capsule-v2 -->
# Template function invocation — how a `{{ plugin.func ... }}` block resolves, invokes, and wraps failures at render time

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** When template rendering executes an in-prompt function call, how are lookup failures and invocation failures distinguished — and does the caller's argument bag survive?

## Copy-on-call with two-layer exception wrapping
**Path/Symbol:** `python/semantic_kernel/template_engine/blocks/code_block.py:CodeBlock._render_function_call` (117–137); outer wrap in `python/semantic_kernel/prompt_template/kernel_prompt_template.py:KernelPromptTemplate.render_blocks` (121–126).
**Signature:** `async def _render_function_call(self, kernel: "Kernel", arguments: "KernelArguments") -> str`.
**Data Shape:** Success returns `str(result) if result else ""` (falsy results render as empty string, `False`/`0`/`None` included). Failures raise CodeBlockRenderException, which render_blocks re-wraps as TemplateRenderException.

### Decisive source
```python
try:
    function = kernel.get_function(function_block.plugin_name, function_block.function_name)
except (KernelFunctionNotFoundError, KernelPluginNotFoundError) as exc:
    error_msg = f"Function `{function_block.content}` not found"
    raise CodeBlockRenderException(error_msg) from exc

arguments_clone = copy(arguments)                      # shallow copy before enrichment
if len(self.tokens) > 1:
    arguments_clone = self._enrich_function_arguments(kernel, arguments_clone, function.metadata)
try:
    result = await function.invoke(kernel, arguments_clone)
except Exception as exc:
    raise CodeBlockRenderException(f"Error invoking function `{function_block.content}`") from exc
return str(result) if result else ""
```

**Flow:** Lookup → shallow-copy the bag → enrich (only when args present) → invoke → stringify. The shallow copy means enrichment writes (positional/named argument injection) never leak into the caller's KernelArguments; values themselves are shared by reference, which is exactly what lets raw typed objects flow to the callee. Lookup errors carry the ORIGINAL block content (`plugin.function` form) for diagnosis; invocation errors swallow the underlying message into the generic wrapper but keep the chain.
**Invariant:** The caller's argument dict identity is preserved across rendering — a template that calls three functions leaves the caller's bag untouched except for value-object sharing. Any exception inside a code block is normalized to TemplateRenderException at the render boundary, so prompt rendering has ONE failure type regardless of whether lookup, arity, or user code failed.
**Probe:** `python/tests/unit/prompt_template/test_kernel_prompt_template.py::test_it_renders_code_error` (124–139: raising tool ⇒ pytest.raises(TemplateRenderException)); `::test_it_renders_code_using_variables` (84–100: happy path `foo-F(BAR)-baz`).
**Coverage caveat:** cited paths checked via check_index_coverage — clean.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "render function call get_function enrich arguments clone invoke CodeBlockRenderException", limit: 8, fields: ["signature", "lines"] });
```
(Executed this pass: top hits = `_enrich_function_arguments`, `_render_function_call`, `Kernel.invoke_function_call`.)

## Verdict
Adopt copy-before-enrich plus the two-layer wrapping (block-level typed error → render-level normalized error). Adapt the falsy-to-empty-string rule if your host must distinguish `0`/`False` outputs — SK deliberately flattens them. Omit the direct `kernel.get_function` coupling only if you have an equivalent registry facade; do not skip the copy step.
