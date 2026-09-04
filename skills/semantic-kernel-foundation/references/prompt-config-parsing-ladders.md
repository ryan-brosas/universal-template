<!-- capsule-v2 -->
# Prompt-config parsing ladders — in what order do prompt/config/settings sources win when building a prompt function, and what is validated at load time?

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** A prompt function can be built from a raw prompt string, a YAML blob, a directory, or an explicit config object — which source wins on conflict, and which mistakes fail at load versus at first invoke?

## Constructor resolution ladder
**Path/Symbol:** `python/semantic_kernel/functions/kernel_function_from_prompt.py:KernelFunctionFromPrompt.__init__` (61–140), `rewrite_execution_settings` model_validator (142–168); file constants `PROMPT_FILE_NAME`/`CONFIG_FILE_NAME` (44–45).
**Signature:** `def __init__(self, function_name, plugin_name=None, description=None, prompt=None, template_format="semantic-kernel", prompt_template=None, prompt_template_config=None, prompt_execution_settings=None) -> None`.
**Data Shape:** exactly one of `prompt` / `prompt_template_config` / `prompt_template` must be present. Settings may arrive as a single instance, a Sequence, or a Mapping and are normalized to `{service_id or "default": settings}`.

### Decisive source
```python
if not prompt and not prompt_template_config and not prompt_template:
    raise FunctionInitializationError("The prompt cannot be empty, ...")
if prompt and prompt_template_config and prompt_template_config.template != prompt:
    logger.warning(f"Prompt ({prompt}) and PromptTemplateConfig ({...}) both supplied, "
                   "using the template in PromptTemplateConfig, ignoring prompt.")
if not prompt_template:
    if not prompt_template_config:
        prompt_template_config = PromptTemplateConfig(name=function_name, description=description,
                                                      template=prompt, template_format=template_format)
    elif not prompt_template_config.template:
        prompt_template_config.template = prompt
    prompt_template = TEMPLATE_FORMAT_MAP[prompt_template_config.template_format](
        prompt_template_config=prompt_template_config)
```

**Flow:** require one of the three sources; when both `prompt` and config exist and differ, the CONFIG wins with only a warning (same for a `template_format` mismatch); a bare prompt is promoted into a fresh `PromptTemplateConfig`; the template object is then instantiated from `TEMPLATE_FORMAT_MAP[config.template_format]`. Metadata parameters come from `config.get_kernel_parameter_metadata()` — InputVariables become KernelParameterMetadata whose `type_` is the variable's `json_schema` STRING, so prompt parameters always take the type-name mapping path (see `function-call-schema-projection`). A pydantic `ValidationError` during metadata construction is re-wrapped as `FunctionInitializationError`. The mode-before validator normalizes single/sequence settings into the keyed dict and falls back to the template config's own `execution_settings` when nothing was supplied.
**Invariant:** config beats explicit prompt (warning, never error); the template format is authoritative in the config; per-service settings are keyed by `service_id or "default"` everywhere.
**Probe:** `python/tests/unit/functions/test_kernel_function_from_prompt.py::test_init_no_prompt` (67–73, all three sources absent → FunctionInitializationError); `::test_create_with_multiple_settings` (280–298, settings list lands as per-id `extension_data["temperature"]`).
**Coverage caveat:** Codebase Memory MCP not connected this session; whole-file direct reads used instead of graph snippets (recorded in verification.md).

## from_yaml / from_directory ladders
**Path/Symbol:** `python/semantic_kernel/functions/kernel_function_from_prompt.py:KernelFunctionFromPrompt.from_yaml` (335–358), `from_directory` (360–416).
**Signature:** `@classmethod def from_yaml(cls, yaml_str: str, plugin_name: str | None = None)`; `@classmethod def from_directory(cls, path: str, plugin_name: str | None = None, encoding: str = "utf-8")`.
**Data Shape:** YAML must deserialize to a dict that validates as `PromptTemplateConfig`. A directory must contain BOTH `skprompt.txt` and `config.json`.

### Decisive source
```python
if not config_exists and not prompt_exists:
    raise FunctionInitializationError(f"{PROMPT_FILE_NAME} and {CONFIG_FILE_NAME} files are required ...")
if not config_exists:
    raise FunctionInitializationError(f"{CONFIG_FILE_NAME} files are required ... prompt file is there.")
if not prompt_exists:
    raise FunctionInitializationError(f"{PROMPT_FILE_NAME} files are required ... config file is there.")
function_name = os.path.basename(path)          # DIRECTORY NAME OVERRIDES config.name
with open(config_path, encoding=encoding) as config_file:
    prompt_template_config = PromptTemplateConfig.from_json(config_file.read())
prompt_template_config.name = function_name
with open(prompt_path, encoding=encoding) as prompt_file:
    prompt_template_config.template = prompt_file.read()   # FILE TEXT OVERRIDES config.template
```

**Flow:** `from_yaml`: `yaml.safe_load` → must be a dict → `PromptTemplateConfig(**data)`; a `ValidationError` (e.g. an invalid `template_format` value) is wrapped into `FunctionInitializationError` — bad format names fail HERE, at load. `from_directory`: three distinct error messages distinguish neither-file / prompt-only / config-only; the function name is taken from the directory basename (overriding whatever the config says); config parses via `from_json` (ValueError-wrapped); the prompt file's text becomes `config.template`; the `encoding` parameter (default utf-8) means a wrong encoding raises `UnicodeDecodeError` UNWRAPPED — the only uncaught failure in the ladder.
**Invariant:** both files are mandatory (no partial-directory loading); directory name > config name > nothing; file text > config template.
**Probe:** `python/tests/unit/functions/test_kernel_function_from_prompt.py::test_from_yaml_fail` (322–325, `template_format: something_else` → FunctionInitializationError); `::test_from_directory_prompt_only` (327–339) and `::test_from_directory_config_only` (341–353); `::test_from_directory_encoding_error_handling` (592–610, ascii read of UTF-8 → UnicodeDecodeError); `::test_from_directory_backward_compatibility` (612–630, no-encoding call still works).

## Config validation + default application
**Path/Symbol:** `python/semantic_kernel/prompt_template/prompt_template_config.py:PromptTemplateConfig.check_input_variables` (47–52), `rewrite_execution_settings` field_validator (56–70), `add_execution_settings` (72–77), `get_kernel_parameter_metadata` (79–88); `kernel_function_from_prompt.py:update_arguments_with_defaults` (328–333), called at the top of `_render_prompt` (273).
**Signature:** `def update_arguments_with_defaults(self, arguments: KernelArguments) -> None`.
**Data Shape:** input-variable defaults must be strings; argument filling happens per invoke, before the prompt-rendering filter stack runs.

### Decisive source
```python
for variable in self.input_variables:
    if variable.default and not isinstance(variable.default, str):
        raise TypeError(f"Default value for input variable {variable.name} must be a string.")
# update_arguments_with_defaults: falsy defaults are NEVER applied
for parameter in self.prompt_template.prompt_template_config.input_variables:
    if parameter.name not in arguments and parameter.default not in {None, "", False, 0}:
        arguments[parameter.name] = parameter.default
```

**Flow:** construction rejects non-string input-variable defaults (TypeError); `add_execution_settings(overwrite=False)` silently skips duplicates BUT the trailing `logger.warning("Execution settings already exist and overwrite is set to False")` fires after EVERY successful add — a misleading log, do not rely on it. At invoke time, missing arguments are filled from input-variable defaults, except falsy ones (`None`, `""`, `False`, `0`) which are treated as "no default".
**Invariant:** defaults are strings by contract (the template world is text); an explicit `""` default is indistinguishable from none and will NOT be injected — porters who need empty-string defaults must pass them through arguments.
**Probe:** `python/tests/unit/prompt_template/test_prompt_templates.py::test_add_execution_settings_no_overwrite` (55–63), `::test_get_kernel_parameter_metadata_with_variables_bad_default` (97–103, non-string default → TypeError), `::test_rewrite_execution_settings` (184–202); `python/tests/unit/functions/test_kernel_function_from_prompt.py::test_invoke_defaults` (260–279, default `"test"` applied to a missing argument end to end).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "KernelFunctionFromPrompt from_yaml from_directory PromptTemplateConfig update_arguments_with_defaults execution_settings", limit: 10, fields: ["signature", "name", "file"] });
```
(Not executable this pass — MCP surface absent; recorded as degraded retrieval, command kept byte-for-byte for the next connected pass.)

## Verdict
Adopt the explicit precedence ladder (config > prompt, directory-name > config-name, file-text > config-template), the three-way directory error taxonomy, and the falsy-defaults exclusion in argument filling. Adapt the string-only default rule if your host supports typed defaults, and fix the always-firing add warning rather than porting it. Omit the unwrapped UnicodeDecodeError path — wrap decode failures in your own initialization error so callers get one failure type from the loader.
