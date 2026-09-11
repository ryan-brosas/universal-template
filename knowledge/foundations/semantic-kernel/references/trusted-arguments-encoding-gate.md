<!-- capsule-v2 -->
# Trusted-arguments encoding gate — which argument values get HTML-escaped before a template sees them, and who can opt out?

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** Before template rendering substitutes variables, what is the trust ladder that decides encode-vs-passthrough per argument value?

## Three-level trust ladder over a rebuilt bag
**Path/Symbol:** `python/semantic_kernel/prompt_template/prompt_template_base.py:PromptTemplateBase._get_trusted_arguments` (26–48), `._get_encoded_value_or_default` (62–94), `._is_safe_type` (96–126); dynamic discovery in `python/semantic_kernel/prompt_template/kernel_prompt_template.py:KernelPromptTemplate.model_post_init` (40–64).
**Signature:** `def _get_trusted_arguments(self, arguments: "KernelArguments") -> "KernelArguments"`.
**Data Shape:** Returns a NEW KernelArguments carrying the same `execution_settings`; values are replaced with encoded or exempted versions. Trust flags: template-level `allow_dangerously_set_content: bool = False` on PromptTemplateBase; config-level and per-`InputVariable` flags on PromptTemplateConfig/InputVariable (default False).

### Decisive source
```python
if self.allow_dangerously_set_content:
    return arguments                                   # level 1: whole-template trust
...
for variable in self.prompt_template_config.input_variables:
    if variable.name == name and variable.allow_dangerously_set_content:
        return value                                   # level 2: per-variable trust
if isinstance(value, str):
    return escape(value)                               # level 3: HTML-encode strings
if self._is_safe_type(value):                          # int/float/bool/bytes/datetime/
    return value                                       # timedelta/UUID/Enum/None pass
raise NotImplementedError(...)                         # complex types MUST opt in
```

**Flow:** render_blocks calls `_get_trusted_arguments(arguments or KernelArguments())` FIRST, so every downstream block reads encoded values. Level ordering matters: template trust short-circuits everything; otherwise each name is checked against the config's input_variables list for an explicit exemption; strings are escaped; only a fixed safe-type set passes unescaped; any other object raises NotImplementedError telling the author to opt in or stringify. Note the flag OR-composition inside `_get_encoded_value_or_default`: it also honors config-level allow_dangerously_set_content.
**Invariant:** model_post_init appends a DEFAULT `InputVariable(name=...)` (allow_dangerously_set_content=False, is_required=True) for every `$var` discovered in blocks, deduping case-insensitively against pre-existing names — so dynamically discovered variables are ENCODED by default; an author cannot get passthrough without declaring the variable. The settings dict is carried into the new bag untouched.
**Probe:** `python/tests/unit/prompt_template/test_prompt_template_e2e.py::test_handles_double_encoded_content_in_template` (492–505: `</message>` → `&lt;/message&gt;`, `'` → `&#x27;`, static text untouched); `::test_trusts_all_templates` (464–489: template-level flag passes raw function output too); `test_kernel_prompt_template.py::test_input_variables` (44–48: discovery appends `InputVariable(name="input")`).
**Coverage caveat:** cited paths checked via check_index_coverage — clean.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "trusted arguments encode escape html allow_dangerously_set_content", limit: 12, fields: ["lines"] });
```
(Executed this pass.)

## Verdict
Adopt the three-level ladder and the rebuild-the-bag shape so encoding is invisible to block renderers. Adapt the safe-type set to your host's primitives. Omit nothing on the default-deny for complex objects: it is the load-bearing prompt-injection defense — auto-discovered variables must inherit encode-by-default, exactly as SK's post-init does.
