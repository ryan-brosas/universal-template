<!-- capsule-v2 -->
# Runtime tool injection — orchestrating filesystem + shell tools into one bundle without re-implementing them

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** A code-executing agent must expose filesystem and shell tools to the model, but the actual tool implementations live in separate executor packages. How do you gate which backends are active, wrap them into prompt-facing + execution-namespace bundles, and keep the injection behavior-identical across Lite/Supervisor/Chat?

## The orchestrator
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_agent_core/tools/runtime_tools.py` (`RuntimeBackends` :29-34, `ToolBundle` :37-43, `prompt_tool_dicts` :46-71, `resolve_runtime_backends` :74-99, `build_runtime_tools` :102-157).
**Signature:** `resolve_runtime_backends(settings, configurable) -> RuntimeBackends`; `build_runtime_tools(*, thread_id, backends) -> ToolBundle`.
**Data Shape:** `RuntimeBackends(filesystem: "none"|"host"|"sandbox_remote", shell: "none"|"local"|"native"|"opensandbox")`. `ToolBundle` = `prompt_tools: List[StructuredTool]`, `execution_callables: Dict[name, callable]`, `app_definitions: List[AppDefinition]`.

### Decisive source
```python
# runtime_tools.py:85-99 — exact legacy gating reproduced so all graphs share one injection path
_use_sandbox = _shell_tool_on and (
    (_sandbox_mode == "native") or (_sandbox_mode == "opensandbox" and _opensandbox_on) or (_sandbox_mode == "local")
)
if not _fs_tool_on:
    filesystem = "none"
elif _use_sandbox and _sandbox_mode == "opensandbox":
    filesystem = "sandbox_remote"
else:
    filesystem = "host"
shell = _sandbox_mode if _use_sandbox else "none"

# runtime_tools.py:122-125 — every tool is made awaitable and split into prompt vs execution namespace
fn = ft.coroutine or ft.func
if fn:
    bundle.execution_callables[ft.name] = make_tool_awaitable(fn)
bundle.prompt_tools.extend(fs_tools)
```

**Flow:** `resolve_runtime_backends` reproduces the legacy gating from `advanced_features` (+ optional `configurable["enable_filesystem_tools"]` override). `build_runtime_tools` then: if filesystem != none, creates filesystem tools via `executors.filesystem.create_filesystem_tools` (with a `RemoteSandboxBackend` when `sandbox_remote`), wraps each callable with `make_tool_awaitable`, adds them to the execution namespace + prompt tools + an `AppDefinition(name="filesystem", type="runtime")`; if shell != none, selects the sandbox executor (`native`/`local`/`opensandbox`), calls `create_sandbox_tools` (returns only `run_command`), and wraps those too. `prompt_tool_dicts` converts runtime StructuredTools into the plain dicts Supervisor's jinja template iterates (name, params_str, description, params_doc, response_doc).
**Invariant:** This module orchestrates existing packages — it never re-implements a filesystem or shell tool. The filesystem/shell axes are independent (a split-execution mode can run python locally while shell/FS run remotely). Tools are split into prompt-facing (for the model) vs execution-namespace (callables for the sandbox) so bind-tools metadata never leaks into the code-executor locals.
**Probe:** `tests/tools/test_runtime_tools.py` (301L) and `tests/tools/test_supervisor_tool_provider.py` (164L) pin the injection gating and bundle shape.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "resolve_runtime_backends build_runtime_tools ToolBundle make_tool_awaitable run_command", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the orchestration-only design (delegate tool impls to executor packages), the independent filesystem/shell gating, the prompt-vs-execution-namespace bundle split, and the always-awaitable wrapper. Adapt the sandbox executor selection to your providers. Omit the Supervisor jinja tool-dict conversion unless your prompt template consumes plain dicts.
