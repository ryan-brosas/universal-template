<!-- capsule-v2 -->
# Function-output encoding gate — when is a template function's return value escaped, and why can't quick_render execute code?

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** Function output is model-visible markup — where exactly does the escape happen, which flag governs it, and how does the no-kernel fast path stay safe?

## Escape at the render boundary; static text never escaped
**Path/Symbol:** `python/semantic_kernel/prompt_template/kernel_prompt_template.py:KernelPromptTemplate.render_blocks` (96–130), `.quick_render` (132–151); flag derivation in `python/semantic_kernel/prompt_template/prompt_template_base.py:PromptTemplateBase._get_allow_dangerously_set_function_output` (50–60).
**Signature:** `async def render_blocks(self, blocks, kernel, arguments=None) -> str`; `@staticmethod def quick_render(template: str, arguments: dict[str, Any]) -> str`.
**Data Shape:** Output is one joined string. Flag source: `allow_dangerously_set_content` OR of template-instance flag and config flag (no per-variable dimension for outputs).

### Decisive source
```python
arguments = self._get_trusted_arguments(arguments or KernelArguments())
allow_unsafe_function_output = self._get_allow_dangerously_set_function_output()
for block in blocks:
    if isinstance(block, TextRenderer):
        rendered_blocks.append(block.render(kernel, arguments))   # static text: NEVER escaped
        continue
    if isinstance(block, CodeRenderer):
        try:
            rendered = await block.render_code(kernel, arguments)
        except Exception as exc:
            raise TemplateRenderException(f"Error rendering code block: {exc}") from exc
        rendered_blocks.append(rendered if allow_unsafe_function_output else escape(rendered))
```
```python
blocks = TemplateTokenizer.tokenize(template)
if any(isinstance(block, CodeRenderer) for block in blocks):
    raise ValueError("Quick render does not support code blocks.")
kernel = Kernel()
return "".join([block.render(kernel, arguments) for block in blocks])
```

**Flow:** Two independent gates protect a rendered prompt: arguments are encoded before substitution (see trusted-arguments-encoding-gate) and FUNCTION OUTPUT is escaped after each code block renders. The output gate consults only the two allow_dangerously_set_content flags — there is deliberately NO per-function opt-out. Static TextBlocks pass through raw, so authors write real XML/markup prompts while untrusted substituted content and untrusted tool output are both neutralized. quick_render tokenizes fresh, refuses any code block with ValueError (it has no plugin registry to invoke against), and fabricates an empty Kernel for text/var rendering only.
**Invariant:** The asymmetry between the two gates is the contract: argument trust is per-variable refinable; output trust is all-or-nothing per template+config. A porter who adds per-function output exemptions breaks SK's security posture; one who escapes static text breaks every structured prompt.
**Probe:** `python/tests/unit/prompt_template/test_prompt_template_e2e.py::test_handles_double_encoded_content_in_template` (492–505 — substituted value escaped, literal `&amp;#x3a;` in static text preserved verbatim); `::test_trusts_all_templates` (464–489 — flag passes raw tool output); `test_kernel_prompt_template.py::test_it_renders_code_error` (124–139 — TemplateRenderException normalization).
**Coverage caveat:** cited paths checked via check_index_coverage — clean.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "render_blocks trusted arguments dangerously set function output quick render", limit: 10, fields: ["lines"] });
```
(Executed this pass.)

## Verdict
Adopt boundary-level escaping with the two-flag OR for output trust, and keep quick-render's refuse-code-blocks stance as the pattern for kernel-less template utilities. Adapt escape() to your target markup (SK uses html.escape). Omit per-variable logic from the output gate on purpose — its absence is the design.
