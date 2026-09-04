<!-- capsule-v2 -->
# Prompt execution settings conversion — how does one generic settings bag become each provider's typed settings?

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** A caller writes provider-neutral settings (temperature, max_tokens, ...) — what protocol moves those values into a specific provider's settings class, and which direction wins on merge?

## extension_data as the neutral bag, pack/unpack as the two-way bridge
**Path/Symbol:** `python/semantic_kernel/connectors/ai/prompt_execution_settings.py:PromptExecutionSettings.__init__` (52–66), `.unpack_extension_data` (107–116), `.pack_extension_data` (118–122), `.update_from_prompt_execution_settings` (89–95), `.from_prompt_execution_settings` (97–105), `.prepare_settings_dict` (73–87), `.parse_function_choice_behavior` (39–50); service-side hook `python/semantic_kernel/services/ai_service_client_base.py:AIServiceClientBase.get_prompt_execution_settings_class` (35–40).
**Signature:** `def __init__(self, service_id: str | None = None, **kwargs: Any)`; `@classmethod def from_prompt_execution_settings(cls, config) -> _T`.
**Data Shape:** Three fields: `service_id` (min_length=1 when set), `extension_data: dict[str, Any]`, `function_choice_behavior` (excluded from dumps). Provider subclasses add typed fields (temperature, top_p, ...).

### Decisive source
```python
def __init__(self, service_id=None, **kwargs):
    extension_data = kwargs.pop("extension_data", {})
    function_choice_behavior = kwargs.pop("function_choice_behavior", None)
    extension_data.update(kwargs)          # temperature=0.5 lands in extension_data
    super().__init__(service_id=..., extension_data=..., function_choice_behavior=...)
    self.unpack_extension_data()           # promote keys that match model fields

def unpack_extension_data(self):           # bag -> typed attributes
    for key, value in self.extension_data.items():
        if value is None: continue         # None never overwrites
        if key in self.keys:               # keys == model_fields.keys()
            setattr(self, key, value)

def pack_extension_data(self):             # typed attributes -> bag
    for key in self.model_fields_set:
        if key not in ["service_id", "extension_data"] and getattr(self, key) is not None:
            self.extension_data[key] = getattr(self, key)

def update_from_prompt_execution_settings(self, config):
    if config.service_id is not None:
        self.service_id = config.service_id
    config.pack_extension_data()
    self.extension_data.update(config.extension_data)   # RHS wins per key
    self.unpack_extension_data()
```

**Flow:** construction funnels every kwarg through extension_data first, then unpack promotes only keys that exist as model fields (unknown keys stay bag-only; None values are skipped so an explicit None cannot clobber a default). Conversion between settings objects always packs the SOURCE then constructs/updates the target from its bag — so a generic `PromptExecutionSettings(temperature=0.5)` becomes `OpenAIChatPromptExecutionSettings(temperature=0.5)` with every other provider field left at its own default. `prepare_settings_dict` is the outbound direction: model_dump excluding service_id/extension_data/structured_json_response, dropping None, by alias. `function_choice_behavior` accepts a string or dict at validation time and is parsed via FunctionChoiceBehavior.from_string/from_dict.
**Invariant:** the bag is the single source of truth during conversion — pack-before-merge guarantees a source's explicitly-set typed fields travel even though they were set as attributes; merge direction is always "config into self" with config winning per key and service_id copied only when non-None. Provider-side field validation (e.g. OpenAI best_of > number_of_responses raising ServiceInvalidExecutionSettingsError) fires both at init and on manual attribute assignment.
**Probe:** `python/tests/unit/connectors/ai/test_prompt_execution_settings.py::test_init_with_data` (bag round-trip); `python/tests/unit/connectors/ai/open_ai/test_openai_request_settings.py::test_openai_chat_prompt_execution_settings_from_default_completion_config` (71–83: conversion of an empty generic bag leaves ALL provider fields None — no phantom defaults), `::test_openai_chat_prompt_execution_settings_from_custom_completion_config` (104–129: nine extension_data keys promoted onto typed fields), `::test_openai_chat_prompt_execution_settings_from_openai_prompt_execution_settings` (85–91: update_from merges service_id + temperature, RHS wins), `::test_openai_text_prompt_execution_settings_validation_manual` (98–102: post-init attribute set still validates).
**Coverage caveat:** Codebase Memory MCP not connected this session; whole-file direct reads used instead of graph snippets (recorded in verification.md).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "PromptExecutionSettings pack_extension_data unpack_extension_data from_prompt_execution_settings", limit: 10, fields: ["signature", "name", "file"] });
```
(Not executable this pass — MCP surface absent; recorded as degraded retrieval, command kept byte-for-byte for the next connected pass.)

## Verdict
Adopt the neutral-bag + pack/unpack bridge: it is what lets one settings object serve N providers and makes selection-time conversion (`settings_class.from_prompt_execution_settings(settings)`) a one-liner. Adapt the exclusion list in prepare_settings_dict to your host's wire format. Omit nothing from the None-skip rule in unpack: it is the difference between "unset" and "explicitly null" and silently breaking it changes provider behavior.
