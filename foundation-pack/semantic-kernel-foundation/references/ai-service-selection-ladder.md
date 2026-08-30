<!-- capsule-v2 -->
# AI service selection ladder — when several services are registered and settings name several of them, which one wins?

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** Given a function with per-service execution settings and a caller's argument bag, how does the kernel pick exactly one (service, settings) pair — and what happens to ids that name unregistered services?

## First-come-first-served scan over a merged settings dict
**Path/Symbol:** `python/semantic_kernel/services/ai_service_selector.py:AIServiceSelector.select_ai_service` (24–69, whole file 69 ln); consumer wrapper `python/semantic_kernel/services/kernel_services_extension.py:KernelServicesExtension.select_ai_service` (52–66).
**Signature:** `def select_ai_service(self, kernel, function=None, arguments=None, type_=None) -> tuple[AIServiceClientBase, PromptExecutionSettings]`.
**Data Shape:** `type_` may be a class or tuple of client-base classes; `None` means "any of the four completion bases". Returns the service instance plus settings converted to THAT service's own settings class. Failure: `KernelServiceNotFoundError("No service found.")` only after every id in the merged dict has been tried.

### Decisive source
```python
if type_ is None:
    type_ = (TextCompletionClientBase, ChatCompletionClientBase,
             TextToAudioClientBase, TextToImageClientBase)   # bare AIServiceClientBase EXCLUDED
execution_settings_dict = arguments.execution_settings if arguments and arguments.execution_settings else {}
if func_exec_settings := getattr(function, "prompt_execution_settings", None):
    for id, settings in func_exec_settings.items():
        if id not in execution_settings_dict:                # arguments win per service_id
            execution_settings_dict[id] = settings
if not execution_settings_dict:
    execution_settings_dict = {DEFAULT_SERVICE_NAME: PromptExecutionSettings()}
for service_id, settings in execution_settings_dict.items(): # dict insertion order = priority
    try:
        if (service := kernel.get_service(service_id, type=type_)) is not None:
            settings_class = service.get_prompt_execution_settings_class()
            if isinstance(settings, settings_class):
                return service, settings
            return service, settings_class.from_prompt_execution_settings(settings)
    except KernelServiceNotFoundError:
        continue                                             # skip unregistered ids, keep scanning
raise KernelServiceNotFoundError("No service found.")
```

**Flow:** merge argument-bag settings first, then fill in function-level settings only for ids not already present; an empty result degrades to `{default: PromptExecutionSettings()}`; scan the merged dict in insertion order; each id resolves through `kernel.get_service` (which itself applies the type filter and the default fallback — see `service-registry-default-fallback`); the first resolvable id wins and its settings are converted into that service's own settings class before returning.
**Invariant:** arguments ALWAYS beat function settings for the same service_id; unregistered ids are silently skipped, never fatal — fatality is reserved for "nothing resolved at all". The `type_ is None` default tuple deliberately excludes bare `AIServiceClientBase` instances, so a kernel holding only abstract test services cannot be selected without an explicit type.
**Probe:** `python/tests/unit/services/test_ai_service_selector.py::test_select_ai_service_no_default_default_types` (raises KernelServiceNotFoundError for a bare AIServiceClientBase with no type given); `::test_select_ai_service_no_default` (non-"default" id still selected when type_=AIServiceClientBase explicit); `python/tests/unit/functions/test_kernel_function_from_prompt.py::test_create_with_multiple_settings_one_service_registered` (300–320: settings list names "test" then "test2", only "test2" registered → invoke succeeds on "test2", proving skip-on-not-found end to end).
**Coverage caveat:** Codebase Memory MCP not connected this session; whole-file direct reads used instead of graph snippets (recorded in verification.md).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "select_ai_service execution_settings DEFAULT_SERVICE_NAME first come first served", limit: 10, fields: ["signature", "name", "file"] });
```
(Not executable this pass — MCP surface absent; recorded as degraded retrieval, command kept byte-for-byte for the next connected pass.)

## Verdict
Adopt the merge-then-scan shape: caller settings override function settings per id, insertion order encodes preference, missing ids are skipped, and exhaustion is the only hard error. Adapt the default type tuple to your host's service families (SK's four completion bases are product-specific). Omit nothing from the conversion step: returning settings in the SELECTED service's own class is what lets one generic PromptExecutionSettings bag drive heterogeneous providers.
