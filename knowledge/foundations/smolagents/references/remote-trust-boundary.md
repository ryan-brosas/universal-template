<!-- capsule-v2 -->
# Local executor vs remote trust boundary — when must a CodeAgent leave the host, and what changes at that line?

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory `ext-smolagents`. **Question:** What is the documented capability/security difference between LocalPythonExecutor and the remote family, and which features are REMOTE-ONLY (managed agents) or LOCAL-ONLY?

## The boundary contract
**Path/Symbol:** `src/smolagents/local_python_executor.py:LocalPythonExecutor` docstring (:1688-1706: "It is not a security sandbox"); `agents.py:create_python_executor` (:1598-1618: managed-agent refusal for ALL remotes), executor_type Literal (:1516); `remote_executors.py` module surface.
**Signature:** `executor_type ∈ {"local","blaxel","e2b","modal","docker"}`; local ctor takes additional_authorized_imports/max_print_outputs_length/additional_functions/timeout_seconds; remotes take (additional_imports, logger, allow_pickle).
**Data Shape:** Both satisfy `PythonExecutor` ABC: send_tools/send_variables/`__call__(code)->CodeOutput`; CodeAgent treats them interchangeably (:1726).

### Decisive source
```python
# agents.py :1607-1609 — the feature cliff is explicit:
else:
    if self.managed_agents:
        raise Exception("Managed agents are not yet supported with remote code execution.")
# local_python_executor.py :1692-1694 — and so is the trust line:
# It is not a security sandbox: for isolated execution of untrusted code, use a remote executor.
```

**Flow:** Selection is purely constructor-time (`executor_type` + `executor_kwargs`); the run loop never branches on it. Local keeps state across steps in-process (variables/functions persist), enforces the allowlist ladder, and trusts the host. Remotes re-establish tool definitions each session (`get_tools_definition_code`), serialize variables/final answers through SafeSerializer prefixes, and trade the restriction ladder for VM/container isolation — but lose managed agents entirely. Cleanup differs per backend yet every one exposes cleanup() reached via CodeAgent context manager (`__enter__/__exit__→cleanup`) or explicit call.
**Invariant:** The ABC is the portability seam — anything added to ONE executor's contract (e.g. `.state` introspection used by CodeAgent error salvage :1735) must be optional-guarded with hasattr because remote executors legitimately lack it. Choosing "local" for untrusted prompts contradicts the module's own docstring regardless of the import ladder.
**Probe:** `tests/test_agents.py::test_local_python_executor_with_custom_functions` (:2237+), remote unit suites (`test_remote_executors.py::TestRemotePythonExecutor`). Live: construct CodeAgent(executor_type="docker", managed_agents=[...]) → Exception before any Docker call.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-smolagents", query: "create_python_executor executor_type LocalPythonExecutor remote", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt single-ABC executor interchangeability with capability cliffs stated where they exist. Adapt backend set freely. Never market the local ladder as sandboxing — smolagents' own docs forbid it.
