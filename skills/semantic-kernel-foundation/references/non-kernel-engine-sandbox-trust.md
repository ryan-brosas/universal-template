<!-- capsule-v2 -->
# Non-Kernel engine sandbox & trust — what safety and lifecycle differences should a porter expect between the Jinja2 and Handlebars engines?

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** Both Jinja2 and Handlebars prompt templates bind the same kernel functions under the same trust gates — where do the two engines differ in sandboxing, when syntax errors surface, how functions are named, and which helpers can shadow which?

## Sandbox, compile timing, naming, helper precedence
**Path/Symbol:** `python/semantic_kernel/prompt_template/jinja2_prompt_template.py:Jinja2PromptTemplate.model_post_init` (61–66) + `render` (68–115); `python/semantic_kernel/prompt_template/handlebars_prompt_template.py:HandlebarsPromptTemplate.model_post_init` (53–64) + `render` (66–113).
**Signature:** both `async def render(self, kernel: Kernel, arguments: KernelArguments | None = None) -> str`.
**Data Shape:** each engine holds one private attribute — `_env` (Jinja2) or `_template_compiler` (Handlebars) — set to None when the template string is empty, in which case `render` returns `""` silently.

### Decisive source
```python
# Jinja2: sandboxed env at construction, PARSE AT RENDER TIME
self._env = ImmutableSandboxedEnvironment(loader=BaseLoader(), enable_async=True)
...
helpers.update(JINJA2_SYSTEM_HELPERS)            # system FIRST → plugins CAN shadow them
for plugin in kernel.plugins.values():
    helpers.update({
        function.fully_qualified_name.replace("-", "_"): create_template_helper_from_function(  # hyphen → underscore
            function, kernel, arguments, self.prompt_template_config.template_format,
            allow_unsafe_function_output, enable_async=True),
        for function in plugin})
template = self._env.from_string(self.prompt_template_config.template, globals=helpers)
return await template.render_async(**arguments)  # TemplateError → Jinja2TemplateRenderException

# Handlebars: COMPILE AT CONSTRUCTION TIME (PybarsError → HandlebarsTemplateSyntaxError)
self._template_compiler = Compiler().compile(self.prompt_template_config.template)
...
for plugin in kernel.plugins.values():
    helpers.update({function.fully_qualified_name: create_template_helper_from_function(...)})  # hyphens KEPT
helpers.update(HANDLEBAR_SYSTEM_HELPERS)          # system LAST → system WINS
return self._template_compiler(arguments, helpers=helpers)   # PybarsError → HandlebarsTemplateRenderException
```

**Flow:** both validate `template_format` at construction (ValueError on mismatch). Jinja2 builds an `ImmutableSandboxedEnvironment` (sandboxed, async-capable) at construction but defers `from_string` to render time, so template SYNTAX errors surface at render as `Jinja2TemplateRenderException`; it rewrites FQN hyphens to underscores because `plugin-function` is not a legal Python identifier (`plug_getLightStatus`). Handlebars compiles the whole template in `model_post_init`, so syntax errors fail at CONSTRUCTION as `HandlebarsTemplateSyntaxError`; FQN hyphens are kept (`plug-getLightStatus`). Helper precedence is asymmetric: Jinja2 seeds system helpers first and then overwrites with plugin functions (plugins CAN shadow system helpers); Handlebars does the reverse (system helpers always win). Both call `PromptTemplateBase._get_trusted_arguments` before rendering — the argument trust gate from `trusted-arguments-encoding-gate` generalizes to these formats — and pass `_get_allow_dangerously_set_function_output()` into the helper factory.
**Invariant:** empty template renders to `""` without error in both engines; the argument trust gate runs BEFORE any helper assembly; a complex (non-safe-type) argument value raises `NotImplementedError` from the gate regardless of engine.
**Probe:** `python/tests/unit/prompt_template/test_jinja2_prompt_template.py::test_it_renders_kernel_functions_arg_from_template` (108–115, underscore FQN call `plug_getLightStatus(arg1='test')`); `python/tests/unit/prompt_template/test_handlebars_prompt_template.py::test_it_renders_kernel_functions_arg_from_template` (114–121, hyphen FQN call `plug-getLightStatus arg1='test'`); `::test_complex_type_encoding_throws_exception` (447–469, dict argument → NotImplementedError from the trust gate); `::test_safe_types_are_allowed` (473–481, int/bool pass through unescaped).
**Coverage caveat:** Codebase Memory MCP not connected this session; whole-file direct reads used instead of graph snippets (recorded in verification.md).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "Jinja2PromptTemplate ImmutableSandboxedEnvironment HandlebarsPromptTemplate Compiler compile JINJA2_SYSTEM_HELPERS HANDLEBAR_SYSTEM_HELPERS", limit: 10, fields: ["signature", "name", "file"] });
```
(Not executable this pass — MCP surface absent; recorded as degraded retrieval, command kept byte-for-byte for the next connected pass.)

## Verdict
Adopt the shared skeleton (format validation at construction, trust-gated arguments, escape-by-default helpers via `template-helper-binding`) and keep the per-engine differences deliberate: sandboxed deferred-parse for the Python-native engine, eager compile for the JS-grammar engine. Adapt the FQN renaming to your identifier rules and CHOOSE a helper-precedence policy explicitly — SK's asymmetry (plugins-can-shadow in Jinja2, system-wins in Handlebars) is an accident of update order, not a designed rule. Omit the silent `""` return for empty templates if your host prefers a loud failure.
