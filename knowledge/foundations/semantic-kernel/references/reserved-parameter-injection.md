<!-- capsule-v2 -->
# Reserved parameter injection — `kernel` / `service` / `execution_settings` / `arguments` come from context, never from user input

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** How can a plugin tool receive the kernel, the selected AI service, or the live arguments without those names being model-fillable?

## gather_function_parameters reserved-name short-circuits
**Path/Symbol:** `python/semantic_kernel/functions/kernel_function_from_method.py:gather_function_parameters` (lines 152–169).
**Signature:** `def gather_function_parameters(self, context: FunctionInvocationContext) -> dict[str, Any]`.
**Data Shape:** Input is the invocation context (function, kernel, arguments); output is the exact kwargs dict passed to the tool. Four reserved parameter names are matched BEFORE any user-argument lookup.

### Decisive source
```python
for param in self.parameters:
    if param.name == "kernel":
        function_arguments[param.name] = context.kernel
        continue
    if param.name == "service":
        function_arguments[param.name] = context.kernel.select_ai_service(self, context.arguments)[0]
        continue
    if param.name == "execution_settings":
        function_arguments[param.name] = context.kernel.select_ai_service(self, context.arguments)[1]
        continue
    if param.name == "arguments":
        function_arguments[param.name] = context.arguments
        continue
```

**Flow:** Each declared parameter is checked against reserved names first: `kernel` gets the live kernel instance; `service` and `execution_settings` are resolved as tuple elements 0/1 of `select_ai_service(function, arguments)` — i.e., service selection happens per-invocation, driven by the caller's execution settings, not at registration; `arguments` receives the whole KernelArguments object. Only non-reserved names fall through to user-argument lookup.
**Invariant:** A reserved name shadows any same-named user argument — the model can never inject a fake kernel/service through tool-call JSON. Conversely, tools that declare a required reserved name always get it satisfied regardless of caller arguments.
**Probe:** `python/tests/unit/functions/test_kernel_function_from_method.py::test_service_execution` (223–246) registers a real OpenAI service with `temperature=0.5`, then asserts inside the tool that it received a `Kernel`, the service instance, settings whose `.temperature == 0.5`, and the KernelArguments object.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "gather_function_parameters select_ai_service reserved", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt a reserved-name injection list for host-context dependencies in tools; resolve per-invocation services lazily from current execution settings rather than baking them into the function. Adapt the name set to your host (e.g., add `context`, `memory`) but keep them checked before user arguments. Omit nothing here lightly: allowing user/model data to override these names is an injection bug.
